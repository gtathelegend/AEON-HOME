# Backend — ÆON Snapdragon Edge AI Engine

The backend is the **cognitive core** of ÆON Home. It runs entirely on the
Snapdragon X Elite AI PC and orchestrates every intelligent subsystem.

## Module map

| Module       | Path            | Responsibility                                              |
|--------------|-----------------|-------------------------------------------------------------|
| API          | `api/`          | FastAPI HTTP endpoints consumed by the PWA dashboard        |
| Serial       | `serial/`       | USB-serial bridge — reads FeatureFrames from Arduino        |
| QNN          | `qnn/`          | Qualcomm Neural Network runtime wrapper (Hexagon NPU)       |
| Models       | `models/`       | Model definitions, quantisation scripts, ONNX → QNN export  |
| Policy       | `policy/`       | Rule engine — generates actuation decisions from AI output  |
| Learning     | `learning/`     | Continuous on-device learning loop (federated-ready)        |
| Graph        | `graph/`        | Knowledge graph — entity relationships, preference model    |
| Migration    | `migration/`    | Identity migration: export / import user profile            |
| Memory       | `memory/`       | Persistent memory store (SQLite, survives power loss)       |
| Voice        | `voice/`        | Sarvam AI speech bridge (STT + TTS, local-first)            |
| Metrics      | `metrics/`      | Prometheus-compatible telemetry exporter                    |
| WebSocket    | `websocket/`    | Real-time event bus to PWA dashboard                        |
| Auth         | `auth/`         | JWT capability tokens, chain-of-trust verification          |
| Config       | `config/`       | Environment configuration, secrets management               |

## Quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m aeon.main
```

## Architecture principles

- **Offline first** — every module degrades gracefully without network.
- **Privacy first** — raw sensor data never leaves this machine.
- **Modular** — each module exposes a clean Python interface and is independently testable.
- Cloud AI 100 integration is in `learning/cloud_sync.py` and is **opt-in**.

## Python version

Requires Python ≥ 3.11 (for `tomllib`, `asyncio.TaskGroup`).
