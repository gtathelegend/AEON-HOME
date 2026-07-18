# ÆON Home — Persistent Edge Intelligence Platform

> Smart devices forget. ÆON remembers.

ÆON Home is a persistent edge AI platform powered by Snapdragon X Elite.
The smart home is the demonstration. The actual innovation is an AI system
that survives power loss, continuously learns on-device, preserves user
privacy, and allows portable identity across devices.

**Everything important happens on the Snapdragon X Elite. The cloud is optional.**

---

## Repository structure

```
aeon-home/
  arduino/              Sentinel firmware (sensing, EEPROM persistence, serial)
    firmware/           Main sketch
    libraries/          aeon_protocol, aeon_checkpoint, aeon_sensors, aeon_features

  backend/              Snapdragon Edge AI Engine (Python, FastAPI)
    aeon/
      api/              REST API (FastAPI) consumed by PWA + mobile
      auth/             JWT capability token system
      config/           Environment configuration
      graph/            On-device knowledge graph (NetworkX + SQLite)
      learning/         Continuous learning loop + Cloud AI 100 sync
      memory/           SQLite persistent memory store (WAL, power-safe)
      metrics/          Prometheus telemetry exporter
      migration/        Identity export/import (signed bundles)
      models/           QNN model definitions + ONNX→QNN export pipeline
      policy/           Policy engine (AI scores + rule overlay → decisions)
      qnn/              QNN SDK wrapper (Hexagon NPU, ONNX CPU fallback)
      serial/           USB-serial bridge + binary protocol parser
      voice/            Sarvam AI speech bridge (STT + TTS)
      websocket/        Real-time WebSocket event bus → PWA dashboard

  frontend/             PWA Dashboard (TanStack Start, React, Tailwind)
    lib/                API client, WebSocket hook
    (src/ is the live TanStack Start source — see frontend/README.md)

  shared/               Cross-layer contracts
    schemas/            JSON Schema for all data structures
    protocol/           AEON binary serial protocol specification
    types/              TypeScript types (mirrors backend dataclasses)

  docs/                 Architecture, privacy model, getting-started guide
  deployment/           systemd service, Docker Compose, nginx config
  tests/                pytest (backend), vitest (frontend), Unity (Arduino)
  scripts/              Setup, flash, test, model-export automation
```

## Core principles

| Principle      | Implementation                                              |
|----------------|-------------------------------------------------------------|
| Edge AI first  | QNN Runtime on Hexagon NPU; cloud is opt-in                |
| Privacy first  | Raw data never leaves Arduino; only capability tokens shared|
| Offline first  | SQLite + EEPROM persistence; zero cloud dependency         |
| Modular        | Every module exposes a clean API; independently testable   |

## Quick start

```bash
# 1. Flash Arduino Firmware
./scripts/flash_arduino.sh /dev/ttyUSB0

# 2. Flash ESP8266 Wi-Fi Gateway
# (Open arduino/esp8266/aeon_wireless_gateway in Arduino IDE, copy config.example.h to config.h, add Wi-Fi details, and upload)

# 3. Set up backend
./scripts/setup_backend.sh

# 4. Start backend
cd backend && source .venv/bin/activate && python -m aeon.main

# 5. Start dashboard
npm install && npm run dev
# → http://localhost:3000
```

See [docs/getting-started.md](docs/getting-started.md) for the full guide.

## System architecture

```
PIR / DHT22 / Reed switch
        ↓
  Arduino Sentinel          (sensing, feature extraction, EEPROM checkpoint)
        ↓  UART (JSON)
  ESP8266 Gateway           (Wi-Fi bridging, offline buffering)
        ↓  WebSocket over Wi-Fi
  Snapdragon X Elite        (QNN/Hexagon NPU, policy, graph, learning, auth)
        ↓  WebSocket / HTTP
  PWA Dashboard + Mobile    (UI only — all intelligence is on-device)
        ↓  text only
  Sarvam Voice              (STT + TTS speech I/O)
        ↕  opt-in
  Qualcomm Cloud AI 100     (background model optimisation)
```

## Privacy model

- Raw sensor data: stays on Arduino.
- Feature vectors: stay on Snapdragon.
- Capability tokens (signed intents, no data): cross the LAN.
- Cloud AI 100: receives model weight deltas only (opt-in, default off).

See [docs/privacy.md](docs/privacy.md) for full details.

## License

Apache 2.0 — see LICENSE.
