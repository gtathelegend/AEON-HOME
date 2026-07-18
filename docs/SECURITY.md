# Security Model & Threat Mitigation

ÆON Home treats safety and privacy as primary system constraints. This document details the threat models, encryption boundaries, and mitigation protocols.

---

## 1. Local LAN & Capability Token Model

To prevent raw device capture and protect user privacy:
- **Zero Raw Data Exchange**: Raw PIR (motion) or DHT11 sensor readings are restricted to the local node (Arduino) and host (Snapdragon X Elite).
- **Capability Tokens**: Outer networks only consume signed JWT intents representing capability events (e.g. `presence.detected`) with strict expiration timestamps (default 1 hour).
- **Verification**: Host API verifies token signatures before executing actions or changing policies.

---

## 2. Firmware-to-Host HMAC Signatures

All telemetry and commands exchanged between the host and firmware can be optionally wrapped with a **SHA-256 HMAC signature**:
- **Signing Secret**: Loaded from `AEON_JWT_SECRET` or settings, shared only between the host gateway and firmware.
- **Timestamp Validation**: Prevent replay of old payloads; packets with a time deviation exceeding 120 seconds are rejected.
- **Nonce tracking**: The host keeps a sliding set of used nonces to completely eliminate duplicate execution windows.

---

## 3. Secrets Management

- **No Plaintext Secrets**: API keys (e.g. Sarvam API credentials) and JWT secrets must be loaded exclusively via environment variables (`.env`).
- **Production Warning**: Defaults (`CHANGE_ME_IN_PRODUCTION`) must be replaced prior to deployment.
