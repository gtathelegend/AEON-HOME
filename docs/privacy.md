# Privacy Architecture

ÆON Home is designed around a **zero-raw-data-sharing** model.

## What stays where

| Data type          | Stays on       | Never leaves         |
|--------------------|----------------|----------------------|
| Raw sensor values  | Arduino        | Arduino              |
| Feature vectors    | Snapdragon PC  | Snapdragon PC        |
| Model weights      | Snapdragon PC  | Unless cloud_sync=true |
| Weight deltas      | Snapdragon PC  | Cloud AI 100 (opt-in) |
| Capability tokens  | All devices    | LAN only             |
| Voice audio        | Snapdragon PC  | Unless SARVAM_OFFLINE=false |
| Voice transcript   | Snapdragon PC  | Snapdragon PC        |

## Capability token model

Instead of sharing sensor data, ÆON shares **signed intents**:

```
"Motion detected with 92% confidence at 09:43"
```

A capability token encodes:
- **What** happened (capability name)
- **How confident** the AI is
- **Why** the decision was made (human-readable reason)
- **When** it expires

The token is a signed JWT. The private key never leaves the Snapdragon.
Any device on the LAN can verify a token without contacting an external service.

## Cloud AI 100 (opt-in)

When `AEON_CLOUD_SYNC=true`:
- Only **model weight deltas** are uploaded — not feature vectors, not tokens.
- Uploads are authenticated with a device-scoped JWT.
- The cloud does background optimisation (pruning/distillation) and returns improved weights.

To disable permanently: set `AEON_CLOUD_SYNC=false` (the default).

## Sarvam voice

When `SARVAM_OFFLINE=false`:
- Audio is sent to the Sarvam API for transcription.
- The transcription is processed locally.
- No sensor data or feature vectors are included.

When `SARVAM_OFFLINE=true` (the default):
- All speech processing happens on-device using an offline STT engine.

## Audit log

Every capability token issued is logged in `aeon_memory.db` (table: `decisions`).
Users can query this via the Privacy Audit dashboard page.
