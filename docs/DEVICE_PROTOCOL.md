# ÆON Home Device Protocol

All communication between the Arduino, ESP8266 Gateway, and Snapdragon backend occurs using one-line, newline-delimited JSON messages.

## Arduino -> Snapdragon (Telemetry)

### `heartbeat`
Sent periodically (every ~5 seconds) to indicate the Arduino is alive.
```json
{
  "protocol_version": 1,
  "typ": "heartbeat",
  "device_id": "sentinel-01",
  "sequence": 100,
  "uptime_ms": 50000,
  "model_v": 2
}
```

### `sensor_update`
Sent continuously as sensors are read. Used by the Snapdragon PC to extract statistical features and run NPU AI inference.
```json
{
  "protocol_version": 1,
  "typ": "sensor_update",
  "device_id": "sentinel-01",
  "sequence": 101,
  "temp": 26.4,
  "humidity": 61.2,
  "motion": 1,
  "model_v": 2
}
```

### `memory_status`
Sent on boot to prove persistent recovery from EEPROM.
```json
{
  "typ": "memory_status",
  "device_id": "sentinel-01",
  "status": "restored",
  "model_v": 2,
  "checksum_valid": true
}
```

### `model_ack` / `policy_ack`
Sent after applying a command from the backend.
```json
{
  "typ": "model_ack",
  "command_id": "uuid-1234",
  "model_v": 3,
  "status": "applied"
}
```

## Snapdragon -> Arduino (Commands)

### `model_update`
Sent by the learning engine when a new statistical threshold or model is trained.
```json
{
  "typ": "model_update",
  "command_id": "uuid-1234",
  "model_v": 3,
  "mean": 25.0,
  "std": 1.2,
  "theta": 28.5
}
```

### `policy_update`
Sent by the dashboard or policy engine to force a threshold change.
```json
{
  "typ": "policy_update",
  "command_id": "uuid-5678",
  "theta": 30.0
}
```

## ESP8266 Gateway Metadata

### `gateway_register`
Sent once on WebSocket connection.
```json
{
  "typ": "gateway_register",
  "gateway_id": "aeon-esp-01",
  "device_id": "sentinel-01",
  "transport": "uart_wifi",
  "firmware_version": "1.0.0"
}
```

### `gateway_status`
Sent periodically by the ESP8266 to report health.
```json
{
  "typ": "gateway_status",
  "gateway_id": "aeon-esp-01",
  "wifi_rssi": -52,
  "arduino_connected": true,
  "uptime_ms": 50000
}
```
