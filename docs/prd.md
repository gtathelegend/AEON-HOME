# ÆON Home — Product Requirements Document

**Persistent Edge Intelligence Platform Powered by Snapdragon AI**

| Field            | Value                                                   |
| :--------------- | :------------------------------------------------------ |
| Version          | 1.0                                                     |
| Status           | Active Development                                      |
| Target Platform  | Snapdragon X Elite (Hexagon NPU) + Arduino UNO Q        |
| Hackathon        | Snapdragon Multiverse Hackathon                          |
| License          | Open Source                                              |

---

## 1. Problem Statement

India's tier-2 and tier-3 cities face **3–5 hours of daily power cuts**. When the power returns, every smart device cold-boots from zero — its learned behavior erased. Current smart home platforms stream raw sensor data to the cloud, violating the **Digital Personal Data Protection (DPDP) Act 2023**. And no two devices share the same intelligence about the user.

These are not bugs. They are **architectural failures** of a computing model that treats intelligence as a cloud service, not an edge-native property.

---

## 2. Solution — Persistent Edge Intelligence

ÆON Home is a **persistent edge intelligence platform** that runs entirely on Snapdragon AI. It demonstrates that a smart environment can:

1. **Survive power loss** with zero reboot loss (< 10 ms recovery)
2. **Prove zero raw data** ever leaves the sensor (cryptographic audit)
3. **Learn continuously on-device** without any cloud dependency
4. **Migrate digital identity** across devices without cloud sync

> The smart home is the demonstration. The platform is the innovation.

---

## 3. Core Design Principles

| Principle             | Implementation                                                             |
| :-------------------- | :------------------------------------------------------------------------- |
| **Edge AI First**     | All inference runs locally on Snapdragon X Elite Hexagon NPU               |
| **Offline First**     | Core intelligence works completely without internet                        |
| **Privacy First**     | Raw sensor data never leaves the Arduino; only signed capability tokens    |
| **Persistence First** | Full execution context is checkpointed to non-volatile memory (EEPROM)     |
| **Cloud Optional**    | Qualcomm AI Cloud 100 is used only for overnight background optimization   |

---

## 4. Why Snapdragon?

The entire ÆON intelligence stack runs on-device, powered by the **Snapdragon X Elite**:

- **All AI inference runs locally** — no internet required
- **Real-time, low-latency** — decisions happen in milliseconds, not round-trips to a data center
- **Privacy-preserving by design** — raw data never leaves the edge
- **NPU acceleration** — QNN Runtime offloads inference to the Hexagon NPU for maximum efficiency
- **Continuous local learning** — the system adapts to user feedback and environmental changes without any cloud dependency
- **Energy efficient** — tokenized alerts replace continuous data streaming, reducing radio energy by an estimated 95%

---

## 5. System Architecture

### 5.1 Device Roles

| Device                | Role                                                                                                              |
| :-------------------- | :---------------------------------------------------------------------------------------------------------------- |
| **Arduino UNO Q**     | Sensing, local anomaly flagging, feature extraction, state persistence (EEPROM checkpoint), actuation             |
| **Snapdragon X Elite** | Core intelligence: QNN inference (Hexagon NPU), token verification, knowledge graph, policy engine, orchestration |
| **Mobile Device**     | User interface: Sarvam voice (STT/TTS), real-time PWA dashboard, onboarding, identity migration                  |

### 5.2 Communication Topology

```
Arduino ↔ ESP8266      Serial (UART, 9600 baud, JSON)
ESP8266 ↔ Snapdragon     WebSocket (local network, JSON)
Snapdragon ↔ Mobile      WebSocket + HTTP (local network, no cloud intermediary)
Snapdragon ↔ Cloud       HTTPS (optional, offline by default)
Mobile ↔ Sarvam          HTTPS (speech I/O only — no sensor data transmitted)
```

### 5.3 Edge AI Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     Arduino UNO Q (MCU)                         │
│  PIR Sensor ─┐                                                  │
│  DHT22 ──────┤→ Feature Extraction → EEPROM Checkpoint          │
│  Door Reed ──┘      (mean, var, delta)                          │
│                          │                                      │
│              UART JSON frames (9600 baud)                       │
└──────────────────────────┼──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                     ESP8266 Wi-Fi Gateway                       │
│              WebSocket JSON (local network)                     │
└──────────────────────────┼──────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│              Snapdragon X Elite Edge AI Engine                   │
│                                                                  │
│  WS Gateway  ────→ JSON payload parser                           │
│       │                                                          │
│       ↓                                                          │
│  QNN Runtime (Hexagon NPU)                                       │
│    ├── presence_classifier.bin                                   │
│    ├── anomaly_detector.bin                                      │
│    └── occupancy_predictor.bin                                   │
│       │                                                          │
│       ↓                                                          │
│  Policy Engine ──→ Capability Token (JWT)                        │
│       │                                                          │
│       ├──→ Knowledge Graph (NetworkX, local SQLite)              │
│       ├──→ Memory Store (persistent local state)                 │
│       ├──→ Continuous Learning Loop (on-device fine-tune)        │
│       └──→ WebSocket Bus → PWA Dashboard                         │
│                                                                  │
│  Sarvam Voice Bridge (STT/TTS — speech I/O only)                 │
│  Metrics Exporter (Prometheus /metrics)                          │
│  Identity Migration (signed JSON + SHA-256 digest + JWT)         │
└──────────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│                   PWA Dashboard (Mobile / Desktop)               │
│  TanStack Start + React + Recharts + shadcn/ui                   │
│  Offline-first service worker (sw.js)                            │
│  Installable Web App (manifest.webmanifest)                      │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. Key Innovations

### 6.1 Persistent Edge State

**Problem**: Every smart device loses its learned behavior on power cut.

**Solution**: The Arduino checkpoints full execution context (sequence counters, feature accumulators, sensor calibration) to EEPROM every 2 seconds. On boot, `checkpoint_restore()` reloads state and resumes operation as if nothing happened. Recovery latency target: **< 10 ms**.

**Implementation**: [`arduino/firmware/sentinel/sentinel.ino`](../arduino/firmware/sentinel/sentinel.ino) — `checkpoint_save()` and `checkpoint_restore()` using `<EEPROM.h>`.

### 6.2 Privacy-by-Design Token Mesh

**Problem**: Current smart home platforms stream raw sensor data to the cloud, violating DPDP Act 2023.

**Solution**: Raw sensor data never leaves the Arduino. The Snapdragon Edge AI Engine processes feature vectors (abstracted from raw readings) and issues **signed capability tokens** (JWTs) that encode *what happened* and *why*, but never the raw sensor values.

**Implementation**: [`backend/aeon/auth/tokens.py`](../backend/aeon/auth/tokens.py) — `CapabilityToken` model with `issue_token()` and `verify_token()` functions. Each token contains: `capability`, `confidence`, `reason`, `device_id`, `issued_at`, `expires_at`.

**Privacy guarantee**: A live audit dashboard proves **0 KB raw data transmitted** since installation.

### 6.3 Portable Cognitive Identity

**Problem**: No two devices share the same intelligence about the user. Switching devices means starting from zero.

**Solution**: User preferences are stored in a local, encrypted knowledge graph. The entire learned profile can be exported as a signed JSON bundle (SHA-256 digest + JWT signature) and imported on any other ÆON device via QR code + biometric approval. Zero cloud sync required.

**Implementation**: [`backend/aeon/migration/migrator.py`](../backend/aeon/migration/migrator.py) — `Migrator.export()` produces a self-contained signed bundle; `Migrator.import_bundle()` validates signature, verifies content digest, and imports the graph.

### 6.4 Background Edge Optimization (Dream State)

**Problem**: On-device models cannot improve without cloud retraining.

**Solution**: During idle periods (overnight), the system replays the day's events and fine-tunes a lightweight adapter layer on top of frozen base model weights. All training uses feature vectors only — never raw sensor data. Cloud AI 100 sync is opt-in.

**Implementation**: [`backend/aeon/learning/loop.py`](../backend/aeon/learning/loop.py) — `LearningLoop` collects labelled samples from user feedback (false alarm corrections) and runs parameter-efficient fine-tuning every 6 hours when ≥ 20 new samples are available.

---

## 7. AEON Protocol (JSON WebSocket Gateway)

JSON-based protocol between Arduino, ESP8266 Gateway, and Snapdragon backend over Wi-Fi WebSocket.

### JSON Structure

```json
{
  "protocol_version": 1,
  "typ": "sensor_update",
  "device_id": "sentinel-01",
  "sequence": 42,
  "temp": 24.5,
  "humidity": 45.2,
  "motion": 1,
  "model_v": 1
}
```

### Frame Types

| Value               | Direction             | Payload                          |
| :------------------ | :-------------------- | :------------------------------- |
| `sensor_update`     | Arduino → Snapdragon  | Temperature, humidity, motion    |
| `heartbeat`         | Arduino → Snapdragon  | Uptime                           |
| `gateway_status`    | ESP8266 → Snapdragon  | Wi-Fi RSSI, Arduino connection   |
| `policy_update`     | Snapdragon → Arduino  | Sensitivity threshold update     |
| `model_update`      | Snapdragon → Arduino  | Feature normalization updates    |

Arduino sends `sensor_update` at ~2 Hz. ESP8266 sends `gateway_status` every 5 seconds.

---

## 8. Backend Subsystems

The Snapdragon backend (`backend/aeon/`) runs as a single async Python process using `asyncio.TaskGroup` to manage concurrent subsystems:

| Subsystem            | Module                        | Responsibility                                             |
| :------------------- | :---------------------------- | :--------------------------------------------------------- |
| **WS Gateway**       | `aeon.api.routes.gateway`     | Async WebSocket endpoint for ESP8266, parses JSON frames   |
| **QNN Runtime**      | `aeon.qnn.runtime`            | Hexagon NPU inference via QNN SDK; ONNX CPU fallback       |
| **Policy Engine**    | `aeon.policy.engine`          | Feature → inference → rule overlay → decision → token      |
| **Knowledge Graph**  | `aeon.graph.knowledge_graph`  | NetworkX-based user preference and context graph           |
| **Memory Store**     | `aeon.memory.store`           | Persistent SQLite state store for decisions and labels      |
| **WebSocket Bus**    | `aeon.websocket.bus`          | Real-time event push to PWA dashboard                      |
| **Voice Bridge**     | `aeon.voice.sarvam_bridge`    | Sarvam AI STT/TTS with offline fallback (Vosk/piper-tts)   |
| **Auth Tokens**      | `aeon.auth.tokens`            | JWT capability token issuance and verification              |
| **Learning Loop**    | `aeon.learning.loop`          | On-device adapter fine-tuning every 6 hours                 |
| **Cloud Sync**       | `aeon.learning.cloud_sync`    | Optional AI Cloud 100 background model refinement           |
| **Migration**        | `aeon.migration.migrator`     | Signed JSON identity export/import                          |
| **Metrics Exporter** | `aeon.metrics.exporter`       | Prometheus metrics endpoint on port 9090                    |
| **FastAPI Server**   | `aeon.api.app`                | REST API on port 8000 for dashboard and mobile              |

### AI Models

Three lightweight models are deployed as QNN context binaries (`.bin`) for Hexagon NPU execution, with ONNX (`.onnx`) CPU fallback for development:

| Model                    | Task                                          |
| :----------------------- | :-------------------------------------------- |
| `presence_classifier`    | Binary classification: person present or not  |
| `anomaly_detector`       | Anomaly scoring on environmental feature vectors |
| `occupancy_predictor`    | Multi-class occupancy pattern prediction       |

---

## 9. Frontend — PWA Dashboard

### 9.1 Technology Stack

- **Framework**: TanStack Start (React, file-based routing)
- **Styling**: Tailwind CSS + shadcn/ui primitives
- **Charts**: Recharts (line, area, bar, radial)
- **Build**: Vite 8 + Nitro (Cloudflare deployment ready)
- **PWA**: Service worker (`sw.js`) + Web App Manifest

### 9.2 Dashboard Routes

| Route                     | Page                     | Data Source                                |
| :------------------------ | :----------------------- | :----------------------------------------- |
| `/dashboard`              | Overview                 | NPU latency, EEPROM, learning, privacy     |
| `/dashboard/onboarding`   | Onboarding Wizard        | Hardware pairing, privacy consent, voice    |
| `/dashboard/serial`       | Arduino Serial Status    | UART connection, sensor streams, EEPROM    |
| `/dashboard/npu`          | Snapdragon NPU Status    | Hexagon NPU speed, QNN model, memory       |
| `/dashboard/voice`        | Sarvam Voice Assistant   | STT/TTS controls, Hindi/English/Tamil      |
| `/dashboard/privacy`      | Privacy Audit Mesh       | 0 KB proof, capability token log           |
| `/dashboard/selfgraph`    | Knowledge Graph           | Portable cognitive identity visualization  |
| `/dashboard/migration`    | Identity Migration       | QR export, biometric validation            |
| `/dashboard/dream`        | Dream State & Learning   | False alarm feedback, model compression    |
| `/dashboard/devices`      | System Nodes             | All device cards with live status           |
| `/dashboard/alerts`       | Alert Mesh               | Signed capability alerts with false-alarm  |
| `/dashboard/metrics`      | Live Metrics             | NPU latency, EEPROM allocation charts      |
| `/dashboard/pulse`        | Persistent Pulse         | Recovery latency, power-cut survivability   |
| `/dashboard/settings`     | Settings                 | Device prefs, privacy, voice, PWA config   |

### 9.3 Real-Time WebSocket Integration

All dashboard components consume live telemetry from `ws://localhost:8000/ws/telemetry` via the [`use-aeon-websocket.ts`](../frontend/src/lib/use-aeon-websocket.ts) reactive hook. The hook provides:

- **Live state streams**: Serial UART, Snapdragon NPU, Sarvam Voice, Knowledge Graph, Continuous Learning, Dream State, Privacy Audit, Migration
- **User action callbacks**: `sendFalseAlarmFeedback()`, `triggerNightMode()`, `triggerIdentityMigration()`, `sendVoiceQuery()`, `setVoiceLanguage()`
- **Offline simulation**: Automatic local mock streaming when backend is disconnected

### 9.4 PWA Capabilities

- **Installable**: Web App Manifest with standalone display mode
- **Offline**: Service worker caches static assets and provides fallback shell
- **Responsive**: Optimized for mobile, tablet, and desktop viewports
- **Install Prompt**: Floating install button with download icon

---

## 10. Demo Story — Intelligence on Snapdragon

1. **Sensors detect an anomaly** — temperature spike or motion detected by Arduino
2. **Snapdragon Edge AI Engine identifies it locally** — inference runs on the Hexagon NPU. No cloud round-trip
3. **User asks "What happened?" in Hindi** — Sarvam STT converts speech to text; the Snapdragon engine processes the query and Sarvam TTS replies aloud
4. **User marks "False Alarm"** via physical button or phone tap
5. **Model adapts immediately** — the sensitivity threshold is adjusted and persisted to EEPROM
6. **Power is removed** — the Arduino loses power completely
7. **Power returns** — the Persistent Edge State restores the entire learned model and execution context. The device resumes as if nothing happened
8. **Identity migrates** — a new phone scans a QR code, biometric approval is given, and all preferences instantly appear on the new device. No cloud sync

---

## 11. Snapdragon Technologies Used

| Technology                | Role in ÆON                                                         |
| :------------------------ | :------------------------------------------------------------------- |
| **Snapdragon X Elite NPU** | Accelerates all edge AI inference via QNN Runtime (Hexagon HTP)     |
| **Qualcomm AI Cloud 100**  | Optional overnight background model retraining                      |
| **Qualcomm AI Hub**        | Reference models (MobileNet-style lightweight architectures)        |
| **Sarvam AI**              | On-device voice interface for Indian languages (STT + TTS)          |

---

## 12. Repository Structure

```
aeon-home/
├── arduino/
│   ├── firmware/sentinel/    Arduino Sentinel firmware (.ino)
│   └── libraries/            aeon_sensors, aeon_features C++ libraries
│
├── backend/
│   ├── aeon/                 Python async backend package
│   │   ├── api/              FastAPI REST endpoints and WebSocket Gateway
│   │   ├── serial/           Legacy USB UART bridge (dummy bridge for dashboard compat)
│   │   ├── qnn/              QNN SDK wrapper (Hexagon NPU, ONNX CPU fallback)
│   │   ├── models/           QNN model definitions + ONNX → QNN export pipeline
│   │   ├── policy/           Policy engine (AI scores + rule overlay → decisions)
│   │   ├── graph/            NetworkX knowledge graph
│   │   ├── learning/         Continuous on-device learning loop + cloud sync
│   │   ├── migration/        Identity export/import (signed bundles)
│   │   ├── memory/           Persistent SQLite state store
│   │   ├── voice/            Sarvam AI speech bridge (STT + TTS)
│   │   ├── websocket/        Real-time WebSocket event bus
│   │   ├── auth/             Capability token system (JWT)
│   │   ├── metrics/          Prometheus metrics exporter
│   │   └── config/           Pydantic settings + .env configuration
│   └── requirements.txt
│
├── frontend/                 PWA Dashboard (TanStack Start, React, Tailwind)
│   ├── public/               manifest.webmanifest, sw.js, icons
│   ├── src/
│   │   ├── components/       Dashboard section components (glassmorphism UI)
│   │   ├── routes/           File-based TanStack router pages
│   │   ├── lib/              WebSocket hook, utilities
│   │   └── hooks/            useInView, useMobile
│   ├── package.json
│   └── vite.config.ts
│
├── shared/                   Cross-layer contracts
│   ├── schemas/              JSON Schema (feature_frame, capability_token)
│   ├── protocol/             AEON binary serial protocol v1 specification
│   └── types/                TypeScript type definitions
│
├── docs/                     Architecture, privacy model, getting-started, PRD
├── deployment/               systemd service, Docker Compose, Dockerfile
├── tests/                    pytest (backend), vitest (frontend)
└── scripts/                  setup_backend, flash_arduino, export_models, run_tests
```

---

## 13. Configuration

All configuration is environment-driven via Pydantic Settings ([`backend/aeon/config/settings.py`](../backend/aeon/config/settings.py)):

| Variable              | Default                | Purpose                                |
| :-------------------- | :--------------------- | :------------------------------------- |
| `AEON_DEVICE_ID`      | `aeon-home-001`        | Unique device identifier               |
| `AEON_API_HOST`       | `0.0.0.0`              | API server bind address                |
| `AEON_API_PORT`       | `8000`                 | API server port                        |
| `AEON_SERIAL_PORT`    | `/dev/ttyUSB0`         | Arduino USB UART port                  |
| `AEON_SERIAL_BAUD`    | `115200`               | Serial baud rate                       |
| `AEON_USE_NPU`        | `true`                 | Enable Hexagon NPU (false = ONNX CPU) |
| `AEON_MODEL_DIR`      | `backend/models/bin`   | QNN/ONNX model directory               |
| `AEON_MEMORY_DB`      | `backend/data/aeon_memory.db` | SQLite state database           |
| `AEON_JWT_SECRET`     | *(must set)*           | Token signing secret                   |
| `SARVAM_API_KEY`      | *(optional)*           | Sarvam AI API key                      |
| `SARVAM_OFFLINE`      | `true`                 | Use offline STT/TTS fallback           |
| `AEON_CLOUD_SYNC`     | `false`                | Enable optional Cloud AI 100 sync      |
| `AEON_METRICS_PORT`   | `9090`                 | Prometheus metrics port                |

---

## 14. Privacy & Compliance

### DPDP Act 2023 Compliance

- **Data Minimization**: Raw sensor data (temperature, humidity, motion) is processed on-device and never transmitted beyond the Arduino → Snapdragon serial link
- **Purpose Limitation**: Only signed capability tokens (intention abstractions) leave the edge node
- **Verifiable Audit**: The PWA dashboard provides a live audit log proving 0 KB raw data transmitted since installation
- **Consent**: Onboarding wizard includes explicit privacy consent step
- **Portability**: Identity migration exports are user-initiated and encrypted

### Capability Token Privacy Model

```
RAW DATA (sensor readings)
    ↓ stays on Arduino
FEATURE VECTORS (mean, variance, delta)
    ↓ stays on Snapdragon (serial link only)
CAPABILITY TOKENS (signed JWT: "what happened" + "confidence")
    ↓ transmitted to dashboard/mobile
```

An intercepted token reveals only the capability (e.g., "motion detected, confidence 0.92") — never the underlying sensor stream.

---

## 15. Why We Win

- **Technical depth**: Measurable persistence (< 10 ms recovery), verifiable privacy (live audit), continuous learning, cross-device identity migration
- **Innovation**: Four novel, demonstrated capabilities that no existing smart home product offers
- **Multi-device orchestration**: Arduino, Snapdragon, mobile, and optional cloud each play a unique, essential role
- **Real-world applicability**: Solves India's power-cut crisis, complies with DPDP Act, and works offline
- **Open source ready**: Modular architecture with clean APIs, documented protocols, and comprehensive test coverage
