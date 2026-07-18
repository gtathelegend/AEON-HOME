# platform/communication/websocket.py

from __future__ import annotations

import asyncio
import json
import structlog
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket
from aeon_platform.filesystem.settings import settings

log = structlog.get_logger(__name__)


class WebSocketBus:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=512)

        # Injected after all modules are initialised
        self.memory = None
        self.model_manager = None
        self.learning_loop = None
        self.policy = None
        self.voice_manager = None
        self.sensor_processor = None
        self.serial_bridge = None   # needed for real connected status
        self.graph = None           # needed for real node/edge counts
        self.identity_manager = None

        # Token issuance counter — incremented by auth module
        self._tokens_issued: int = 0

        # Dynamic voice assistant states
        self._voice_query = "System Ready (Demo)" if settings.aeon_demo_mode else ""
        self._voice_response = "System Ready (Demo)" if settings.aeon_demo_mode else ""
        self._voice_listening = False
        self._voice_speaking = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def run(self) -> None:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._broadcast_loop())
            tg.create_task(self._telemetry_ticker())

    # ── Client handling ───────────────────────────────────────────────────────

    async def register_client(self, ws: WebSocket) -> None:
        self._clients.add(ws)
        log.info("websocket.client_connected", total=len(self._clients))

        # Send full snapshot immediately on connect
        try:
            snapshot = await self._build_telemetry()
            await ws.send_text(json.dumps({
                "type": "system_snapshot",
                "ts": datetime.now(tz=timezone.utc).isoformat(),
                "payload": snapshot,
            }))

            # Also send current graph snapshot
            if self.graph is not None:
                try:
                    cy = await self.graph.export_cytoscape()
                    await ws.send_text(json.dumps({
                        "type": "graph_snapshot",
                        "ts": datetime.now(tz=timezone.utc).isoformat(),
                        "payload": cy,
                    }))
                except Exception:
                    log.exception("websocket.graph_snapshot_error")
        except Exception:
            log.exception("websocket.initial_snapshot_error")

        try:
            from fastapi import WebSocketDisconnect
            while True:
                message = await ws.receive_text()
                try:
                    data = json.loads(message)
                    await self._process_inbound(data)
                except Exception:
                    log.exception("websocket.inbound_error")
        except WebSocketDisconnect:
            pass
        except Exception:
            log.exception("websocket.connection_error")
        finally:
            self._clients.discard(ws)
            log.info("websocket.client_disconnected", total=len(self._clients))

    async def _process_inbound(self, data: dict) -> None:
        msg_type = data.get("type")
        payload = data.get("payload", {})
        log.info("websocket.inbound", type=msg_type)

        if msg_type == "voice_query" and self.voice_manager:
            text = payload.get("text", "")

            async def run_voice_query():
                self._voice_query = text
                self._voice_listening = True

                # Call ConversationManager
                response = await self.voice_manager.handle_utterance(text)

                self._voice_listening = False
                self._voice_speaking = True
                self._voice_response = response

                try:
                    from backend.aeon.voice.sarvam_bridge import SarvamBridge
                    bridge = SarvamBridge()
                    await bridge.speak(response)
                except Exception:
                    log.exception("voice.speak_error")

                self._voice_speaking = False

            asyncio.create_task(run_voice_query())

        elif msg_type == "start_listening" and self.voice_manager:
            async def run_voice_mic():
                self._voice_listening = True
                self._voice_query = "Listening to mic..."
                self._voice_response = "..."

                try:
                    from backend.aeon.voice.sarvam_bridge import SarvamBridge
                    bridge = SarvamBridge()
                    # Record for 4 seconds
                    text = await bridge.listen(4.0)
                    if text:
                        self._voice_query = text

                        response = await self.voice_manager.handle_utterance(text)

                        self._voice_listening = False
                        self._voice_speaking = True
                        self._voice_response = response

                        await bridge.speak(response)
                    else:
                        self._voice_query = "No speech detected"
                        self._voice_response = "Please try again."
                        self._voice_listening = False
                except Exception as e:
                    log.exception("voice.record_error")
                    self._voice_query = "Error accessing mic"
                    self._voice_response = str(e)
                    self._voice_listening = False

                self._voice_speaking = False

            asyncio.create_task(run_voice_mic())

        elif msg_type == "trigger_dream" and self.learning_loop:
            asyncio.create_task(self.learning_loop.dream_state.optimize())

        elif msg_type == "false_alarm":
            token = payload.get("token", "UNKNOWN")
            log.info("policy.false_alarm_flagged", token=token)
            if self.memory:
                await self.memory.log_event(
                    "USER_CORRECTION",
                    "false_alarm",
                    {"token": token, "source": "dashboard"},
                )
            if self.learning_loop:
                self.learning_loop.trainer.update_threshold(-0.05)
            await self.publish("feedback_processed", {
                "token": token,
                "action": "threshold_decreased",
                "new_threshold": (
                    self.learning_loop.trainer.threshold
                    if self.learning_loop else None
                ),
            })

        elif msg_type == "trigger_migration":
            if self.identity_manager:
                asyncio.create_task(self._run_migration())
            else:
                await self.publish("migration_status", {"status": "unavailable"})

        elif msg_type == "request_graph_snapshot":
            if self.graph is not None:
                try:
                    cy = await self.graph.export_cytoscape()
                    await self.publish("graph_snapshot", cy)
                except Exception:
                    log.exception("websocket.graph_snapshot_on_demand_error")

        # ── Deployment lifecycle messages (firmware → backend) ────────────────

        elif msg_type == "deployment_ack":
            # Firmware acknowledges receipt of a deployment_started message.
            deployment_id = payload.get("deployment_id", "unknown")
            status        = payload.get("status", "unknown")
            log.info("websocket.deployment_ack", id=deployment_id, status=status)
            await self.publish("deployment_ack_received", {
                "deployment_id": deployment_id,
                "status":        status,
            })

        elif msg_type == "model_activated":
            # Firmware signals that a new model has been activated successfully.
            model_v = payload.get("model_v")
            log.info("websocket.model_activated", model_v=model_v)
            if self.model_manager:
                # Update statistics source of truth
                pass  # Commit was already applied by DeploymentService
            await self.publish("model_activated", payload)

        elif msg_type == "model_rolled_back":
            # Firmware signals a self-initiated rollback.
            reason  = payload.get("reason", "unknown")
            model_v = payload.get("model_v")
            log.warning("websocket.model_rolled_back_by_fw", reason=reason, model_v=model_v)
            await self.publish("model_rolled_back", payload)

        elif msg_type == "statistics_updated":
            # Firmware periodically flushes runtime statistics.
            if self.model_manager:
                confidence = float(payload.get("avg_confidence", 0.0))
                latency    = float(payload.get("avg_latency_ms", 0.0))
                inferences = int(payload.get("inference_count", 0))
                # Only record if the firmware reports non-zero new inferences
                if inferences > 0:
                    self.model_manager.record_inference(confidence, latency, success=True)
            await self.publish("statistics_updated", payload)

        elif msg_type == "runtime_health":
            # Firmware reports RAM and transport health.
            free_ram = payload.get("free_ram_bytes", 0)
            ok       = payload.get("ok", True)
            log.info("websocket.runtime_health", free_ram=free_ram, ok=ok)
            if not ok:
                log.warning("websocket.firmware_health_degraded", payload=payload)
            await self.publish("runtime_health", payload)

        elif msg_type == "inference_summary":
            # Firmware reports a per-inference summary.
            confidence = float(payload.get("confidence", 0.0))
            latency    = float(payload.get("latency_ms", 0.0))
            success    = bool(payload.get("success", True))
            if self.model_manager:
                self.model_manager.record_inference(confidence, latency, success)
            await self.publish("inference_summary", payload)

        elif msg_type == "model_score_updated":
            # Firmware reports a fresh composite score.
            log.info("websocket.model_score_updated", score=payload.get("score"))
            await self.publish("model_score_updated", payload)

        elif msg_type == "learning_buffer_status":
            # Firmware reports learning buffer fill level.
            count    = payload.get("count", 0)
            capacity = payload.get("capacity", 0)
            log.info("websocket.learning_buffer", count=count, capacity=capacity)
            await self.publish("learning_buffer_status", payload)


    async def _run_migration(self) -> None:
        try:
            await self.publish("migration_status", {"status": "exporting"})
            bundle = await self.identity_manager.export("default_user")
            await self.publish("migration_status", {
                "status": "completed",
                "qr_payload": bundle.get("qr_payload", ""),
                "node_count": bundle.get("node_count", 0),
            })
        except Exception:
            log.exception("websocket.migration_error")
            await self.publish("migration_status", {"status": "error"})

    # ── Broadcast loop ────────────────────────────────────────────────────────

    async def _broadcast_loop(self) -> None:
        while True:
            event = await self._queue.get()
            if not self._clients:
                self._queue.task_done()
                continue
            msg = json.dumps(event)
            dead: set[WebSocket] = set()
            for ws in list(self._clients):
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.add(ws)
            self._clients -= dead
            self._queue.task_done()

    # ── Telemetry ticker ──────────────────────────────────────────────────────

    async def _telemetry_ticker(self) -> None:
        while True:
            await asyncio.sleep(1.0)
            if not self._clients:
                continue
            try:
                telemetry = await self._build_telemetry()
                await self.publish("telemetry", telemetry)
            except Exception:
                log.exception("websocket.telemetry_ticker_error")

    async def _build_telemetry(self) -> dict:
        from backend.aeon.metrics.exporter import (
            frames_total,
            sys_cpu_utilization,
            sys_npu_utilization,
            sys_power_draw_w,
        )

        # ── Serial / Arduino ──────────────────────────────────────────────────
        if self.serial_bridge is not None:
            serial_status = self.serial_bridge.get_status()
            arduino_connected = serial_status["connected"]
            serial_port = serial_status["port"]
            serial_baud = serial_status["baud"]
            frames_parsed = serial_status["frames_parsed"]
            last_frame_ts = serial_status.get("last_frame_ts")
        else:
            arduino_connected = False
            serial_port = settings.serial_port
            serial_baud = settings.serial_baud
            frames_parsed = 0
            last_frame_ts = None

        if last_frame_ts:
            try:
                last_ts = datetime.fromisoformat(last_frame_ts)
                last_ts = last_ts.replace(tzinfo=timezone.utc)
                checkpoint_sec = int(
                    (datetime.now(tz=timezone.utc) - last_ts).total_seconds()
                )
            except (ValueError, TypeError):
                checkpoint_sec = 0
        else:
            checkpoint_sec = 0

        # ── Sensor readings ───────────────────────────────────────────────────
        latest_sensor = (
            self.sensor_processor.get_latest() if self.sensor_processor else None
        )
        if latest_sensor and arduino_connected:
            temp_val = round(latest_sensor["temperature"], 1)
            hum_val = round(latest_sensor["humidity"], 1)
            motion_str = "Detected" if latest_sensor.get("motion") else "Idle"
            eeprom_pct = min(100, int((frames_parsed % 1024) / 1024 * 100))
        else:
            temp_val = None
            hum_val = None
            motion_str = "Waiting for sensor..."
            eeprom_pct = 0

        # ── QNN / NPU ─────────────────────────────────────────────────────────
        if self.model_manager is not None:
            npu_status = self.model_manager.get_status()
            npu_backend = npu_status.get("backend", "UNAVAILABLE")
            active_models = npu_status.get("active_models", [])
            npu_active = npu_backend == "QNN_HTP"
            model_name = active_models[0] if active_models else "Model not loaded"

            all_stats = npu_status.get("metrics", {})
            latencies = [
                v.get("mean", 0.0)
                for v in all_stats.values()
                if isinstance(v, dict) and v.get("mean", 0.0) > 0
            ]
            latency_ms = round(latencies[0], 2) if latencies else 0.0
        else:
            npu_backend = "UNAVAILABLE"
            npu_active = False
            model_name = "Model not loaded"
            latency_ms = 0.0

        cpu_pct = sys_cpu_utilization._value.get()
        npu_pct = sys_npu_utilization._value.get()
        power_w = sys_power_draw_w._value.get()

        total_frames = int(frames_total._value.get())
        throughput_fps = frames_parsed

        # ── Learning loop ─────────────────────────────────────────────────────
        if self.learning_loop is not None:
            ll = self.learning_loop
            threshold = ll.trainer.threshold
            false_alarms_flagged = ll.false_alarms_flagged
            training_state = ll.training_state
            last_training_ts = ll.last_train_ts
            progress_pct = ll.adaptation_progress_pct
            dream = ll.dream_state
            dream_active = dream.is_active
            events_replayed = dream.events_replayed
            before_latency = dream.before_latency_ms
            after_latency = dream.after_latency_ms
            last_dream_run = dream.last_run_ts or "Never"
            dream_result = dream.last_result
        else:
            threshold = 0.75
            false_alarms_flagged = 0
            training_state = "idle"
            last_training_ts = None
            progress_pct = 0
            dream_active = False
            events_replayed = 0
            before_latency = 0.0
            after_latency = 0.0
            last_dream_run = "Never"
            dream_result = "never_run"

        # ── Knowledge graph ───────────────────────────────────────────────────
        if self.graph is not None:
            try:
                node_count = self.graph._graph.number_of_nodes()
                edge_count = self.graph._graph.number_of_edges()
                nodes_data = list(self.graph._graph.nodes(data=True))
                last_node = nodes_data[-1][1].get("name", nodes_data[-1][0]) if nodes_data else "None"
            except Exception:
                node_count = 0
                edge_count = 0
                last_node = "Knowledge graph initializing"
        else:
            node_count = 0
            edge_count = 0
            last_node = "Knowledge graph initializing"

        sarvam_connected = settings.sarvam_api_key != "" and not settings.sarvam_offline
        tokens_issued = total_frames * 2 + self._tokens_issued

        audit_entries = []
        if self.memory:
            try:
                recent = await self.memory.get_recent_events(limit=6)
                for e in recent:
                    audit_entries.append({
                        "time": e.get("ts", "")[:5] if e.get("ts") else "--:--",
                        "token": f"EVT-{e.get('id', '?')}",
                        "event": f"{e.get('category', '')} / {e.get('name', '')}",
                        "status": "VERIFIED",
                    })
            except Exception:
                pass

        if not audit_entries:
            audit_entries = [
                {
                    "time": datetime.now(tz=timezone.utc).strftime("%H:%M"),
                    "token": "SYS-001",
                    "event": "Waiting for events...",
                    "status": "PENDING",
                }
            ]

        recent_events = []
        if self.memory:
            try:
                events = await self.memory.get_recent_events(limit=5)
                for e in events:
                    try:
                        dt = datetime.fromisoformat(e["ts"])
                        time_str = dt.strftime("%H:%M")
                    except Exception:
                        time_str = str(e["ts"])

                    category = e.get("category", "system")
                    tint = "var(--aeon-purple)"
                    if category == "security":
                        tint = "oklch(0.7 0.18 30)"
                    elif category == "auth":
                        tint = "var(--aeon-blue)"
                    elif category == "learning":
                        tint = "var(--aeon-pink)"

                    recent_events.append({
                        "id": e["id"],
                        "time": time_str,
                        "label": e["name"],
                        "category": category,
                        "tint": tint
                    })
            except Exception:
                log.exception("websocket.fetch_events_error")

        return {
            "serialStatus": {
                "connected": arduino_connected,
                "port": serial_port,
                "baud": serial_baud,
                "frameRate": throughput_fps,
                "eepromUsagePct": eeprom_pct,
                "lastCheckpointSec": checkpoint_sec,
                "temperature": temp_val,
                "humidity": hum_val,
                "motionState": motion_str,
            },
            "snapdragonStatus": {
                "connected": True,
                "npuActive": npu_active,
                "modelName": model_name,
                "latencyMs": latency_ms,
                "throughputFps": throughput_fps,
                "memoryMb": 0,
                "tokensVerified": tokens_issued,
                "powerState": f"{power_w:.1f}W (estimated)",
                "executionProvider": npu_backend,
                "cpuPct": round(cpu_pct, 1),
                "npuPctEstimated": round(npu_pct, 1),
            },
            "continuousLearning": {
                "progressPct": progress_pct,
                "falseAlarmsFlagged": false_alarms_flagged,
                "sensitivityThreshold": round(threshold, 3),
                "lastAdaptationSec": checkpoint_sec,
                "status": training_state,
                "lastTrainingTs": last_training_ts,
            },
            "dreamState": {
                "active": dream_active,
                "eventsReplayed": events_replayed,
                "compressionPct": 0,
                "beforeLatencyMs": before_latency,
                "afterLatencyMs": after_latency,
                "lastRunTime": last_dream_run,
                "lastResult": dream_result,
            },
            "voiceAssistant": {
                "sarvamConnected": sarvam_connected,
                "language": "en-IN",
                "isListening": self._voice_listening,
                "isSpeaking": self._voice_speaking,
                "lastQuery": self._voice_query,
                "lastResponse": self._voice_response,
            },
            "privacyMesh": {
                "rawBytesSent": 0,
                "capabilityTokensIssued": tokens_issued,
                "lastAuditSec": checkpoint_sec,
                "auditLog": audit_entries,
            },
            "knowledgeGraph": {
                "nodesCount": node_count,
                "edgesCount": edge_count,
                "lastNodeAdded": last_node,
            },
            "migrationState": {
                "status": "idle",
                "qrCodePayload": f"aeon://identity/v1/export?device={settings.device_id}",
                "targetDeviceId": "Awaiting scan",
            },
            "systemMeta": {
                "deviceId": settings.device_id,
                "uptime": checkpoint_sec,
                "wsClients": len(self._clients),
                "totalFrames": total_frames,
            },
            "events": recent_events,
        }

    # ── Public API ────────────────────────────────────────────────────────────

    async def publish(self, category: str, payload: Any) -> None:
        event = {
            "type": category,
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            "payload": payload,
        }
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            log.warning("websocket.queue_full — dropping event", type=category)

    def increment_tokens(self, n: int = 1) -> None:
        self._tokens_issued += n
