# ÆON Home — System Architecture

## Overview

ÆON Home is a **Persistent Edge Intelligence Platform** — a multi-layer system
where a Snapdragon X Elite AI PC acts as the cognitive engine for a network of
Arduino sensors, with a PWA dashboard as the only external interface.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Interface                              │
│         PWA Dashboard (React)        Sarvam Voice (STT/TTS)        │
└────────────────────────────┬──────────────────────┬────────────────┘
                             │ HTTP/WS               │ Text only
┌────────────────────────────▼──────────────────────▼────────────────┐
│                  Snapdragon X Elite — Edge AI Engine                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │ WS       │ │  QNN /   │ │ Policy   │ │Knowledge │ │  Auth   │ │
│  │ Gateway  │→│ Hexagon  │→│ Engine   │ │  Graph   │ │ Tokens  │ │
│  │          │ │  NPU     │ │          │ │          │ │         │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └─────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │Continuous│ │ Memory   │ │WebSocket │ │ Metrics  │             │
│  │ Learning │ │  Store   │ │   Bus    │ │Prometheus│             │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘             │
└────────────────────────────┬────────────────────────────────────────┘
                             │ WebSocket (JSON) over Wi-Fi
┌────────────────────────────▼────────────────────────────────────────┐
│                      ESP8266 Wi-Fi Gateway                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │ UART (JSON, 9600 baud)
┌────────────────────────────▼────────────────────────────────────────┐
│                    Arduino Sentinel                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │  DHT22   │  │  HC-SR501│  │   Reed   │  │  EEPROM          │   │
│  │ Temp/Hum │  │  PIR     │  │  Switch  │  │  Checkpoint      │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                                 ↕ (optional)
                              Qualcomm Cloud AI 100
                              (background optimisation only)
```

## Data flow

1. **Sensors → Feature Extraction (Arduino)**  
   DHT22, PIR, reed switch → rolling window statistics → FeatureFrame struct.  
   Raw sensor values never leave the Arduino.

2. **Feature Frames → QNN Inference (Snapdragon)**  
   FeatureFrame (7 floats) → Hexagon NPU → presence probability + anomaly score.

3. **AI output → Policy Engine**  
   Scores + rule overlay → PolicyDecision.  
   High-confidence decisions → capability token issued.

4. **Policy → WebSocket → Dashboard**  
   Structured events pushed to all connected PWA clients in real time.

5. **User Feedback → Learning Loop**  
   False alarm labels → labelled dataset → periodic fine-tune of QNN adapter.

6. **Dream State (nightly)**  
   All idle devices consolidate the day's decisions.  
   Model weights pruned and compressed overnight.  
   Optional: delta weights sent to Cloud AI 100 for distillation.

## Privacy model

- Raw sensor data stays on Arduino.
- Feature vectors stay on Snapdragon.
- Only capability tokens (intent + confidence, no data) cross any network boundary.
- Cloud AI 100 receives only model weight deltas, never data.

## Persistence and recovery

- Arduino checkpoints state to EEPROM every 2 seconds (ping-pong slots).
- Recovery latency target: **< 200 ms** from power-on.
- Snapdragon memory store uses SQLite with WAL journaling.
- Knowledge graph is rebuilt from SQLite on every boot.
