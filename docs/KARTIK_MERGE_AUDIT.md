# Kartik Branch Final Integration & Merge Audit

This audit document details all files modified or added in the `Kartik` branch, their current state, and the decisions regarding whether to keep, modify, or remove them during the final preparation for the merge into `main`.

---

## Audit Matrix

### 1. Configuration & Seeding

| File | Component / Feature | Current Implementation | Decision | Reason / Action Required |
| :--- | :--- | :--- | :--- | :--- |
| `backend/aeon/config/settings.py` | Config schema settings | Central settings using pydantic-settings | **Modify** | Add `AEON_SEED_DATABASE` flag. |
| `backend/aeon/main.py` | Database initializer | Database seeding call commented out | **Modify** | Bind seeding to `settings.seed_database` instead of commenting it out. |
| `.env.example` | Configuration example | Documented environment variables | **Modify** | Add documentation for `AEON_DEMO_MODE=false` and `AEON_SEED_DATABASE=false`. |
| `backend/aeon/memory/seed.py` | Default DB seeding | Adds old node layout (`arduino`, `esp8266`, `aipc`, `phone`, `cloud`) | **Modify** | Update nodes to reflect modern 4-tier model: Arduino Sentinel (`sentinel`), ESP8266 Wireless Gateway (`gateway`), Snapdragon X Elite Edge Engine (`edge_engine`), and Mobile PWA (`mobile`). Remove Cloud. |

### 2. Telemetry and Backend Processing

| File | Component / Feature | Current Implementation | Decision | Reason / Action Required |
| :--- | :--- | :--- | :--- | :--- |
| `backend/aeon/voice/sarvam_bridge.py` | Voice STT Offline | Uses `random.choice` to pick simulated intents in offline mode | **Modify** | Remove random simulator. Return empty string `""` so that unavailable STT is reported cleanly. |
| `backend/aeon/websocket/bus.py` | Telemetry Builder | Set `npu_active = len(active_models) > 0` | **Modify** | Set `npu_active = npu_backend == "QNN_HTP"` so we do not claim NPU execution on CPU fallback. Clean up estimates. |

### 3. Frontend & PWA Integration

| File | Component / Feature | Current Implementation | Decision | Reason / Action Required |
| :--- | :--- | :--- | :--- | :--- |
| `frontend/src/hooks/use-aeon-telemetry.tsx` | Web telemetry hook | Initialized disconnected temperature/humidity to `0` | **Modify** | Initialize to `null` so UI shows "Waiting for sensor..." instead of `0 °C`. Bind demo mode to environment. |
| `frontend/src/components/dashboard-sections.tsx` | Live Dashboard Sections | V2 dashboard cards, connection status pills, services grid | **Keep & Modify** | Keep improvements; update active devices list to the updated 4 nodes. Label power/NPU estimates clearly. |
| `frontend/src/components/architecture-sections.tsx` | Architecture Panels | Displays 6 layers of telemetry and topology | **Keep & Modify** | Keep panels; update network topology nodes and labels to match the real ESP8266-to-Snapdragon wireless WebSocket/UART path. |

---

## Verification & Hardening Checklist

- [ ] **No silent fallbacks**: Unplugging the ESP8266 gateway must cause the dashboard to display "Waiting for sensor..." and disconnect status pills.
- [ ] **No simulated voice**: Voice queries fail with "Sarvam Voice Service Unavailable" if the API key is empty or offline.
- [ ] **Truthful NPU Metrics**: NPU Active is true *only* when execution provider is `QNN_HTP`.
- [ ] **PWA and desktop sync**: Ensure both views derive from identical WebSocket telemetry.
