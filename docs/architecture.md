# System Architecture Documentation

This document describes the design, subsystems, and data flows of the ÆON Home edge-native cognitive platform.

---

## 1. Overall System Topology

ÆON Home organizes computational tasks across three distinct tiers to maximize offline reliability, user privacy, and hardware acceleration:

```
+------------------+     JSON / WebSocket      +----------------------+
|  Arduino UNO Q   | <=======================> |  Snapdragon X Elite  |
|  (Edge Sentinel) |                           |  (Cognitive OS Host) |
+------------------+                           +----------------------+
  - Sensor Drivers                               - QNN / NPU Runtime
  - Local Fallbacks                              - Explainability Engine
  - EEPROM Checkpoint                            - Knowledge Graph (DB)
```

---

## 2. Runtime & Reasoning Flow

Every telemetry update runs through a **9-stage Cognitive Execution Pipeline** to resolve device actions:

```
[Sensors] 
   │
   ▼
[Feature Extraction] 
   │
   ▼
[Inference Engine (QNN)] 
   │
   ▼
[Context Engine] ──► [Activity Engine] ──► [User Profile Engine] ──► [Policy Engine Overlay]
                                                                            │
                                                                            ▼
                                                                    [Reasoning Engine]
                                                                            │
                                                                            ▼
                                                                    [Device Action]
```

1. **Sensing**: DHT11 and PIR motion sensors sample physical baselines.
2. **Context Engine**: Extracts temporal and spatial contexts.
3. **Activity Engine**: Infers user state (e.g., Sleeping, Away, Working).
4. **User Profile**: Overlay preference settings (e.g. `preferred_temp`).
5. **Policy Engine Overlay**: Combines rules and models.
6. **Reasoning Engine**: Explores 5 alternative outcomes and selects the action.
7. **Explainability Engine**: Formulates textual logs for user transparency.
8. **Actuation**: Transmits output intents to target relays or notification buses.

---

## 3. Communication Gateway

All messages flow through a standardized, version-aware **Communication Gateway**:
- **Protocol**: Raw JSON payloads wrapped with metadata.
- **Security**: Optional HMAC validation, nonces, and timestamp skew tracking.
- **Event Bus**: Emits loose event publishes (`TelemetryReceived`, `DeviceConnected`, `CheckpointSaved`) for background service decoupling.

---

## 4. Dream State & Optimization

When the system detects zero command activity for 10 seconds:
- **Consolidation**: Prunes stale context records.
- **Policy Tuning**: Boosts confidence indicators.
- **Interruption**: Reverts to active mode immediately on user input.
