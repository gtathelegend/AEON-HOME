# backend/aeon/services/communication_gateway.py

from __future__ import annotations

import json
import asyncio
import structlog
from typing import Any, Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

from shared.types import FeatureFrame, AeonEvent

log = structlog.get_logger(__name__)


class CommunicationGateway:
    """
    Authoritative communication layer bridging backend services with the Arduino.
    Handles signature checking, message queue retries, and schema validation.
    """

    def __init__(
        self,
        auth_service: Any,
        telemetry_service: Any,
        learning_service: Any,
        device_service: Any,
        checkpoint_service: Any,
        event_bus: Any,
    ) -> None:
        self.auth_service = auth_service
        self.telemetry_service = telemetry_service
        self.learning_service = learning_service
        self.device_service = device_service
        self.checkpoint_service = checkpoint_service
        self.event_bus = event_bus
        
        self._active_sockets: Set[WebSocket] = set()
        self._message_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=128)

    async def register_connection(self, websocket: WebSocket) -> None:
        self._active_sockets.add(websocket)
        log.info("gateway.connection_opened", client=websocket.client)

    async def deregister_connection(self, websocket: WebSocket) -> None:
        if websocket in self._active_sockets:
            self._active_sockets.remove(websocket)
        log.info("gateway.connection_closed", client=websocket.client)

    async def handle_incoming(self, data: str, websocket: WebSocket | None = None) -> None:
        """Parse, validate signature/auth, and route payload to correct service."""
        try:
            payload = json.loads(data)
            typ = payload.get("typ")
            
            # Enforce Authentication if signature is present
            signature = payload.get("signature")
            if signature:
                timestamp = int(payload.get("timestamp", 0))
                nonce = payload.get("nonce", "")
                raw_payload = payload.get("data", "")
                
                valid = self.auth_service.verify_firmware_hmac(
                    payload=raw_payload,
                    signature=signature,
                    timestamp=timestamp,
                    nonce=nonce
                )
                if not valid:
                    log.warning("gateway.unauthorized_payload_rejected")
                    return
                # Extract internal payload
                payload = json.loads(raw_payload)
                typ = payload.get("typ")

            # Route to respective service
            if typ == "sensor_update":
                frame = FeatureFrame.from_json(payload)
                # Count frames parsed if websocket app state is present
                if websocket is not None and hasattr(websocket, "app") and hasattr(websocket.app.state, "serial_bridge") and websocket.app.state.serial_bridge:
                    websocket.app.state.serial_bridge._frames_parsed += 1
                
                await self.telemetry_service.ingest_frame(frame)

            elif typ == "learning_record":
                device_id = payload.get("device_id", "sentinel_01")
                records = payload.get("records", [payload])
                await self.learning_service.upload_buffer_records(device_id, records)

            elif typ == "checkpoint":
                device_id = payload.get("device_id", "sentinel_01")
                await self.checkpoint_service.synchronize_checkpoint(device_id, payload)

            elif typ == "heartbeat":
                device_id = payload.get("device_id", "sentinel_01")
                await self.device_service.ping(device_id)

            elif typ in ("memory_status", "feedback_event", "model_ack", "policy_ack"):
                event = AeonEvent.from_json(payload)
                # Dispatch event handler callback if websocket app state is present
                if websocket is not None and hasattr(websocket, "app") and hasattr(websocket.app.state, "event_processor") and websocket.app.state.event_processor:
                    await websocket.app.state.event_processor.on_event(event)

        except json.JSONDecodeError:
            log.warning("gateway.invalid_json_received", raw=data)
        except Exception as e:
            log.exception("gateway.routing_error", error=str(e))

    async def send_command(self, cmd: Dict[str, Any]) -> bool:
        """Enqueue command for transmission with retry logic."""
        if not self._active_sockets:
            log.warning("gateway.no_active_sockets — buffering command")
            try:
                self._message_queue.put_nowait(cmd)
            except asyncio.QueueFull:
                log.error("gateway.command_queue_full — command dropped")
            return False

        serialized = json.dumps(cmd)
        disconnected = []
        sent = False
        
        for ws in self._active_sockets:
            try:
                await ws.send_text(serialized)
                sent = True
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            await self.deregister_connection(ws)

        return sent
