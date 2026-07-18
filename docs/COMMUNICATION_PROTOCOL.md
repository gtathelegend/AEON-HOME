# Communication Protocol Documentation

All communication between the edge node (Arduino Sentinel) and the host (Snapdragon Node) uses a structured JSON-based protocol over WebSocket or USB-Serial.

---

## 1. Frame Wrapping & Authentication

Every packet transmitted from the edge can be optionally signed using a SHA-256 HMAC wrapper to enforce request integrity:

```json
{
  "signature": "a6f87d...e92c",
  "timestamp": 1783456723,
  "nonce": "8f39a7b1c",
  "data": "{\"typ\":\"sensor_update\",\"temperature\":22.5,...}"
}
```

### Authentication Protocol
1. **HMAC Signature**: Evaluated as `HMAC-SHA256(Secret, Payload + ":" + Timestamp + ":" + Nonce)`.
2. **Timestamp Verification**: Packets with timestamps deviating by more than 120 seconds from the host system time are discarded.
3. **Nonce De-duplication**: Nonces are stored in a rolling buffer to block replay attacks.

---

## 2. Core Protocol Message Types

### 1. Telemetry (`sensor_update`)
Sent periodically to update environmental conditions:
```json
{
  "typ": "sensor_update",
  "temperature": 23.4,
  "humidity": 45.0,
  "motion": true,
  "door_open": false,
  "seq": 458
}
```

### 2. Checkpoint (`checkpoint`)
Transmitted during state save synchronization:
```json
{
  "typ": "checkpoint",
  "device_id": "sentinel_01",
  "checkpoint_id": 42,
  "valid": true,
  "storage_usage_pct": 12
}
```

### 3. Feedback Received (`feedback_received`)
Transmits classification outcomes of user overrides:
```json
{
  "typ": "feedback_received",
  "feedback_type": "correction",
  "target": "temp",
  "value": 24.5
}
```

### 4. Dream Events (`dream_started` / `dream_completed`)
Signals background optimization phases:
```json
{
  "typ": "dream_completed",
  "duration_ms": 4250,
  "consolidated_memories": 8
}
```
