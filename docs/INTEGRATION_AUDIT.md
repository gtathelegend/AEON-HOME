# ÆON Home — Integration Audit

Generated: 2026-07-17  
Scope: Complete codebase review — every mock, fake, and disconnected path.

---

## Summary

The backend architecture is structurally sound. The serial bridge, QNN manager, policy engine, memory store, knowledge graph, learning loop, and Sarvam bridge are all real implementations. The primary integration failures are:

1. The WebSocket telemetry ticker (`bus.py`) uses random numbers and hardcoded values instead of real backend state.
2. The frontend fallback simulation (`use-aeon-websocket.ts`) silently replaces missing data with `Math.random()` instead of showing disconnected states.
3. Several frontend components display hardcoded strings and static chart data.
4. The Dream State broadcasts no progress stages and applies mock logic.
5. The voice recorder sends `audio/webm` but the backend expects WAV.
6. Privacy metrics (`raw_bytes_sent`, `tokens_issued`) are hardcoded zeros.
7. The knowledge graph visualization is hardcoded SVG nodes — not driven by real graph data.
8. Alerts page has hardcoded static alert list.
9. Dashboard sidebar shows hardcoded "Active (Hexagon)" and "0 KB" strings.

---

## Component-by-Component Audit

### FRONTEND

| Component | File | Current State | Expected State | Mock/Real | Problems | Required Fix |
|---|---|---|---|---|---|---|
| Overview page | `dashboard.index.tsx` | Renders `Overview` component | Live system snapshot | Real (uses WS) | Depends on WS state which has fallback mocks | Fix WS hook and telemetry ticker |
| Dashboard layout sidebar | `dashboard.tsx` | "Active (Hexagon)" hardcoded; "0 KB" hardcoded; "Dream Mode: Idle" hardcoded | Real NPU backend/WS state | **MOCK** | Sidebar status panel is static string literals | Wire sidebar pills to WS telemetry state |
| TopBar status pills | `dashboard.tsx` | "Mesh Network: Local Only"; "Dream Mode: Idle" — hardcoded | Real backend state | **MOCK** | Not connected to any state | Wire to WS state |
| Metrics charts | `dashboard-sections.tsx` L1020-1040 | `Math.random()` + `Math.sin()` used to generate chart series | Historical data from backend `/api/v1/sensors` | **MOCK** | `latencyData` and `eepromData` arrays use Math.random | Replace with real API fetch of sensor/inference history |
| Pulse 24h chart | `dashboard-sections.tsx` | `Math.sin()` used to generate 24h latency series | Real 24h inference latency from backend | **MOCK** | Fake sine wave, not real data | Fetch from `/api/v1/metrics/history` |
| Alerts page | `dashboard-sections.tsx` | Static hardcoded alert array `[CAP-1032, CAP-1031 ...]` | Live events from backend event store | **MOCK** | No backend connection | Fetch from `/api/v1/events` and subscribe to `system_event` WS messages |
| Dream compare chart | `dashboard-sections.tsx` | `before` values hardcoded `[100, 12, 100, 92]` | Real pre/post optimization metrics from dream state | **MOCK** | Static comparison data | Pull from WS `dream_state_complete` event |
| Knowledge graph visualization | `dashboard-sections.tsx` | Hardcoded 5-node SVG with fixed positions | Real graph nodes/edges from backend via WS `graph_snapshot` | **MOCK** | Nodes are static | Subscribe to `graph_snapshot`/`graph_delta` WS events |
| Voice assistant metrics | `dashboard-sections.tsx` | "Sarvam Bridge: 100%", "Inference Engine: 8ms" — hardcoded MetricCard values | Real Sarvam connection status and inference latency | **MOCK** | Static values passed to MetricCard | Wire to WS `voiceAssistant` state |
| VoiceRecorder component | `pwa/VoiceRecorder.tsx` | Sends `audio/webm` blob directly | Backend expects WAV or the route must accept webm | **BROKEN** | MIME type mismatch with `/voice/command` which uses `soundfile.read` | Fix voice route to accept webm OR convert in recorder |
| Migration QR code | `dashboard-sections.tsx` | CSS grid of colored `div` elements (fake QR) | Real QR code generated from `migrationState.qrCodePayload` | **MOCK** | Decorative fake pattern | Use a real QR code library (e.g. `qrcode.react`) |
| WS hook — fallback simulation | `use-aeon-websocket.ts` | `startFallbackSimulation()` uses `Math.random()` in `setInterval` on disconnect | Show "Arduino disconnected" / "Model not loaded" states | **MOCK** | Silently generates fake data when backend is offline | Remove simulation, show disconnected states with status strings |
| WS hook — initial state | `use-aeon-websocket.ts` | `INITIAL_STATE` has `temperature: 21.6`, `latencyMs: 8.4`, etc. | Initial state must reflect "unknown/disconnected" | **MOCK** | Hardcoded plausible-looking values shown before backend connects | Zero/null initial state with appropriate "waiting" labels |
| WS hook — `sendVoiceQuery` | `use-aeon-websocket.ts` | Uses `setTimeout` to fake "Processing → Speaking" states locally | Backend WS should push real voice status updates | **MOCK** | Voice state faked with timers | Remove local faking; wait for WS `voice_status` events from backend |
| WS hook — `triggerIdentityMigration` | `use-aeon-websocket.ts` | Uses `setTimeout(2500)` to fake "biometric_pending → completed" | Backend WS `migration_status` event | **MOCK** | Migration completion simulated with timer | Wait for WS `migration_status` event |
| AutoDiscoveryProvider | `providers/AutoDiscoveryProvider.tsx` | Scans hardcoded IP list, but discovered URL not used by WS hook | WS hook should use discovered URL | **DISCONNECTED** | `wsUrl` from AutoDiscovery is never consumed by `use-aeon-websocket.ts` | Thread discovered WS URL into the WS hook |

### BACKEND

| Component | File | Current State | Expected State | Mock/Real | Problems | Required Fix |
|---|---|---|---|---|---|---|
| WS telemetry ticker | `websocket/bus.py` | `latencyMs: 8.0 + (random.random() * 2)` | Real inference latency from QNN metrics | **MOCK** | `random.random()` in production telemetry | Read from `qnn_manager.metrics.get_stats()` |
| WS telemetry — serial connected | `websocket/bus.py` | `"connected": True` hardcoded | `serial_bridge.connected` property | **MOCK** | Always shows connected even when Arduino is not plugged in | Use `serial_bridge.connected` |
| WS telemetry — dream state | `websocket/bus.py` | `eventsReplayed: 4200`, `beforeLatencyMs: 14.5` hardcoded | Real dream state metrics from learning loop | **MOCK** | Static values | Read from `learning_loop.dream_state` actual results |
| WS telemetry — learning | `websocket/bus.py` | `progressPct: 85`, `falseAlarmsFlagged: 0` hardcoded | Real learning loop counters | **MOCK** | Not reading from `learning_loop` | Add properties to `LearningLoop` and read them |
| WS telemetry — knowledge graph | `websocket/bus.py` | `nodesCount: 24`, `edgesCount: 56` hardcoded | Real `graph.number_of_nodes()` | **MOCK** | Graph object not injected into bus | Inject graph into bus, read real counts |
| WS telemetry — voice | `websocket/bus.py` | `sarvamConnected: True` hardcoded | Real Sarvam API connectivity status | **MOCK** | Not testing Sarvam availability | Add health check to `SarvamBridge`, expose status |
| NPU utilization metric | `metrics/exporter.py` | `cpu * 0.4 + random.uniform(-5, 15)` | Real Hexagon DSP utilization (or clearly labeled estimate) | **MOCK** | Random noise added | Remove random noise; label as estimate; use Snapdragon perf APIs if available |
| Power draw metric | `metrics/exporter.py` | `15.0 + estimate` formula | Real power from hardware sensors or clearly labeled estimate | **MOCK** | Formula-based estimate | Label clearly as estimate; attempt real hardware read |
| Privacy tokens_issued | `api/routes/system.py` | `tokens_issued: 0` hardcoded | Real count from auth token issuance log | **MOCK** | Not reading actual token count | Count from decisions table or token log |
| Dream State stages | `learning/dream.py` | No WS broadcast of progress stages | Broadcast `dream_state_progress` events per stage | **MISSING** | Dashboard can't show live dream stages | Add WS bus to DreamState, broadcast each stage |
| Dream State rules | `learning/dream.py` | `add_rule` call is commented out | Actually write rules to knowledge graph | **MOCK** | Rules never persisted | Implement `graph.add_policy()` call |
| Dream State `corrections` filter | `learning/dream.py` | `e.type == "USER_CORRECTION"` — events have no `.type` attr | Events dict uses `"category"` key | **BUG** | `AttributeError` at runtime — `e` is a dict | Fix to `e.get("category") == "USER_CORRECTION"` |
| Voice feedback handler | `voice/manager.py` | Returns "Thanks for feedback" but does NOT log to SQLite | Should call `memory.label_decision()` or log correction | **DISCONNECTED** | Feedback never persists | Add `_store.log_event("USER_CORRECTION", ...)` call |
| Policy engine override | `policy/engine.py` | `execute_override()` method called by voice manager doesn't exist | Method must exist on PolicyEngine | **MISSING** | `AttributeError` at runtime | Add `execute_override(target, action)` method |
| WS `trigger_migration` handler | `websocket/bus.py` | Sends `{"status": "completed"}` immediately | Should call real `Migrator.export()` | **MOCK** | Migration not actually performed | Wire to `identity_manager` / `Migrator` |
| Serial bridge auto-detection | `serial/bridge.py` | Uses configured `settings.serial_port` only | Should scan common ports if configured port fails | **LIMITED** | No port auto-detection | Add port scanning fallback |
| QNN execution provider | `qnn/manager.py` | Reports "QNN (Hexagon HTP)" string always | Must check `_QNN_AVAILABLE` and actual session type | **PARTIALLY MOCK** | String doesn't reflect actual runtime | Expose real `execution_provider` field |
| Model files missing | `models/` | No `.onnx` or `.bin` files in `backend/models/bin/` | Model files must exist for inference | **BLOCKED** | `ModelLoader.load()` returns `None` for all models | Create ONNX model stubs or real models |

### ARDUINO / FIRMWARE

| Component | File | Current State | Expected State | Mock/Real | Problems | Required Fix |
|---|---|---|---|---|---|---|
| Firmware serial protocol | `sentinel.ino` + protocol libs | Implements AEON binary frame protocol | Working firmware | Real | Needs to be flashed and verified | Hardware-dependent: BLOCKED until Snapdragon machine |
| EEPROM checkpointing | `aeon_checkpoint.*` | Implemented in firmware | Working on hardware | Real | Hardware-dependent | BLOCKED |

---

## Priority Fix List

### P0 — Breaks demo completely
1. Remove `Math.random()` fallback simulation from `use-aeon-websocket.ts`
2. Fix `websocket/bus.py` — use real `serial_bridge.connected`, real graph counts, real QNN latency
3. Fix `dream.py` `AttributeError` — `e.type` → `e.get("category")`
4. Add `execute_override` to `PolicyEngine`
5. Fix VoiceRecorder MIME type / voice route audio handling

### P1 — Shows wrong data in demo
6. Wire sidebar NPU/privacy/dream pills to WS state
7. Replace Metrics chart `Math.random()` with real API history fetch
8. Replace Alerts static array with real event stream
9. Fix privacy `tokens_issued: 0` to real count
10. Wire AutoDiscovery URL to WS hook

### P2 — Missing features
11. Add dream state progress stage broadcasting
12. Add real QR code rendering
13. Add `LearningLoop` counters (false_alarms, progress)
14. Broadcast `graph_snapshot` on WS connect
15. Implement `voice_status` WS events

### P3 — Polish / observability
16. Add correlation IDs to events
17. Add `/api/v1/system/state` central state endpoint
18. Add `execution_provider` field to QNN status
19. Label NPU utilization as "estimated" in UI
