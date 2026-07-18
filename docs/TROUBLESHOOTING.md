# Troubleshooting Guide — Common Issues & Workarounds

This document outlines resolution procedures for common hardware, firmware, and backend connectivity failures in the ÆON Home platform.

---

## 1. WiFi Dropouts and Transport Reconnection

### Symptoms
- The dashboard shows "Connected: false" under serial bridge parameters.
- Inbound telemetry charts go flat.

### Resolution Steps
1. Verify the ESP8266 or Uno R4 WiFi is powered and shows active link status.
2. The firmware automatically attempts Wi-Fi association retries indefinitely on link loss without freezing the local policy engine.
3. If reconnects fail repeatedly, check for physical channel congestion or DHCP address exhaustion.

---

## 2. Checkpoint Corruption (EEPROM Recovery)

### Symptoms
- During boot, the serial logs report:
  `[BOOT] CRC validation failed! Resetting slot storage...`

### Underlying Cause
- Occurs if power loss occurs exactly during an EEPROM write tick or if memory cells degrade.

### Recovery Procedure
- The Sentinel firmware implements **Automatic Ping-Pong Recovery**:
  1. It reads Slot A. If corrupt, it reads Slot B.
  2. If both are invalid, it automatically resets fields to defaults (`resetToDefaults(state)`) and reformats the slots.
  3. No manual flashing is required to restore basic operations.

---

## 3. Model Rollback Spikes

### Symptoms
- Piezo buzzer beeps 3 times repeatedly.
- Inference latency increases beyond 100ms.

### Resolution
- The `RollbackManager` automatically detects the degradation and swaps execution to the default stable model version (Model v1).
- Inspect `backend/models/bin/` to verify that the hot-deployed model was compiled with correct Hexagon NPU dimensions.
