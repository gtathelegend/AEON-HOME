# ÆON Home — Protocol Specification v1.0

The ÆON Protocol is a robust, edge-first communication protocol designed to securely transmit sensor data, AI policies, and distributed state across microcontrollers (Arduino), the Edge AI Engine (Snapdragon), and the user interface (PWA).

## 1. Architectural Layers

The protocol operates in two modes:
1. **Binary Serial Protocol (Microcontroller ↔ Snapdragon):** Highly compressed C-structs framed by COBS/0x7E for maximum UART efficiency. (See `aeon_protocol.h`).
2. **JSON/WebSocket Protocol (Snapdragon ↔ Clients/Nodes):** A full JSON-based protocol used for inter-node routing, dashboard telemetry, and system-to-system syncing. This document details the **JSON Protocol**.

## 2. Core Envelope Schema

Every message must adhere to the standard envelope schema. This ensures versioning, routing, and message signing are uniform across all endpoints.

```json
{
  "version": "1.0",
  "id": "msg_5970c6fb",
  "timestamp": 1713508103000,
  "src": "aeon-home-001",
  "dst": "pwa-client-xyz",
  "type": "event|command|heartbeat|ack|discovery",
  "signature": "hmac_sha256(secret, payload_hash)",
  "payload": { ... }
}
```

### Fields:
- `version`: Protocol version to support backward compatibility.
- `id`: Unique UUID or monotonic ULID for the message (used for retries and ACKs).
- `timestamp`: UTC epoch milliseconds for time synchronization and replay-attack prevention.
- `src` / `dst`: Sender and receiver identifiers. A `dst` of `*` indicates a broadcast (e.g., discovery).
- `type`: The intent of the message.
- `signature`: HMAC-SHA256 signature generated using the pre-shared device key over the concatenated `id + timestamp + payload`.

## 3. Message Types

### 3.1 Device Discovery
Sent over UDP multicast or the central WebSocket broker to find new nodes.
```json
{
  "type": "discovery",
  "payload": {
    "device_class": "sensor_node",
    "capabilities": ["temperature", "humidity", "motion"],
    "ip_address": "192.168.1.55"
  }
}
```

### 3.2 Time Synchronization
The edge engine acts as the NTP master for microcontrollers and offline clients.
```json
{
  "type": "command",
  "payload": {
    "action": "sync_clock",
    "reference_time": 1713508103000
  }
}
```

### 3.3 Heartbeat
Used to maintain connection health and report basic metrics. Sent every 30 seconds.
```json
{
  "type": "heartbeat",
  "payload": {
    "uptime_s": 3600,
    "battery_pct": 98,
    "last_error": null
  }
}
```

### 3.4 Acknowledgements (ACK) & Retries
For critical commands (like Actuation or Policy Updates), the sender requires an ACK. If no ACK is received within `TimeoutMs` (e.g., 500ms), the sender retries up to 3 times, reusing the same `id`.
```json
{
  "type": "ack",
  "payload": {
    "ack_id": "msg_5970c6fb",
    "status": "success",
    "latency_ms": 12
  }
}
```

### 3.5 Command Routing
Commands route intent from the user/AI to a specific actuator.
```json
{
  "type": "command",
  "payload": {
    "target": "relay_1",
    "action": "turn_on",
    "reason": "policy_override",
    "confidence": 0.95
  }
}
```

## 4. Message Signing (Security)
To preserve privacy and prevent unauthorized access on the LAN, all messages must be signed.
1. Compute `hash = SHA256(stringify(payload))`.
2. Compute `signature = HMAC_SHA256(shared_secret, id + timestamp + hash)`.
3. The receiver verifies the signature. If it fails, or if `timestamp` is > 5 minutes old (replay attack), the message is dropped.

## 5. Compression
For the WebSocket layer, payloads that exceed 1024 bytes (e.g., Knowledge Graph profile migrations, or large ML datasets) are compressed.
If compressed, the payload schema becomes:
```json
{
  "type": "migration",
  "payload_encoding": "gzip+base64",
  "payload": "H4sIAAAAAAAA/8tJLS7JzEsHAAwO..."
}
```

## 6. Implementation Guidelines
- **Idempotency**: Because of retries, all `command` handlers must be idempotent (e.g., turning a relay ON twice does nothing).
- **Offline First**: The protocol assumes the cloud is unavailable. `shared_secret` keys are provisioned locally via QR code or physical button press during initial pairing.
