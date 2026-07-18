# ÆON Home — Persistent Edge Intelligence Platform

> Smart devices forget. ÆON remembers.

ÆON Home is a persistent edge AI platform powered by the **Qualcomm Snapdragon X Elite**. The smart home is our demonstration, but the core innovation is an on-device edge operating system that survives power losses, learns continuously through user feedback loops, preserves absolute privacy, and enables portable user identities.

---

## 1. Project Overview & Architecture

Every critical operation (inference, learning optimization, reasoning, and context analysis) occurs directly on the edge node. The cloud remains optional.

```
                  +--------------------------------+
                  |      User Interaction (PWA)    |
                  +--------------------------------+
                                  | HTTP / WebSocket
                                  v
                  +--------------------------------+
                  |  Snapdragon X Elite Node (Host) |
                  |  - REST API & Event Bus        |
                  |  - QNN / NPU Inference Runtime |
                  |  - Context & Activity Engines  |
                  |  - Reasoning & Explanations    |
                  +--------------------------------+
                                  | Wi-Fi (JSON Gateway)
                                  v
                  +--------------------------------+
                  |   Arduino UNO Q (Edge Sentinel)|
                  |  - Persistent Checkpoint (Flash)|
                  |  - Local Policy Controller     |
                  |  - Hardware Driver Layer       |
                  +--------------------------------+
```

---

## 2. Directory Structure

```
aeon-home/
  backend/              Snapdragon Edge AI Engine (Python, FastAPI)
    aeon/
      api/              REST API Layer and WebSocket gateway
      services/         Application Services (Device, Telemetry, Checkpoint, etc.)
      config/           Environment configuration
      graph/            On-device knowledge graph (NetworkX + SQLite)
      learning/         Continuous learning loops
      memory/           SQLite persistent memory store (WAL, power-safe)
      metrics/          Prometheus telemetry exporter
      models/           QNN model definitions and ONNX exports
      policy/           Policy engine
      voice/            Sarvam AI speech bridge (STT + TTS)
  firmware/             Arduino UNO Q firmware (sensing, EEPROM checkpointing)
  frontend/             PWA Dashboard (React, Vite, Tailwind CSS)
  shared/               Cross-layer schemas and protocol contracts
  docs/                 Architecture, privacy model, getting-started guide
  tests/                Full pytest system integration test suite
```

---

## 3. Technology Stack

- **Firmware**: C++ / Arduino API on Qualcomm Arduino Uno Q (STM32U585 MCU)
- **Backend Node**: Python 3.11+, FastAPI, SQLite, NetworkX, Qualcomm QNN SDK
- **Frontend Dashboard**: TypeScript, React, Vite, Tailwind CSS, TanStack Router
- **Speech Processing**: Sarvam AI API for localized voice commands

---

## 4. Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- `arduino-cli` (optional for compilation)

### Setup & Installation

1. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env to set your serial ports and keys
   ```

2. **Backend Installation**:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/Scripts/activate
   pip install -r requirements.txt
   ```

3. **Frontend Installation**:
   ```bash
   cd ../frontend
   npm install
   ```

4. **Flash Firmware**:
   Copy libraries from `firmware/libraries/` to your local Arduino libraries path, then compile and flash the sketch located in `firmware/firmware/sentinel/` using the Arduino IDE.

5. **Start Applications**:
   - Backend: `cd backend && python -m aeon.main`
   - Frontend: `cd frontend && npm run dev`

---

## 5. Verification & Testing

Verify the installation by running the system integration test suite:
```bash
cd backend
.venv/Scripts/pytest
```

---

## 6. License & Roadmap

This project is licensed under the Apache 2.0 License. See `ROADMAP.md` in the `docs` directory for future extensions including Matter protocol integration.
