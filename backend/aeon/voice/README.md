# Voice Module — ÆON Home

## Overview

The voice module integrates **Sarvam AI** for bilingual (English/Hindi) speech interaction.
All intelligence runs on the Snapdragon X Elite edge device — only text strings cross the
Sarvam API boundary. Raw audio and sensor data never leave the local network.

## Architecture

```
Browser mic (MediaRecorder WebM)
        │
        ▼  multipart/form-data upload
POST /api/v1/voice/command
        │
        ├─ _convert_to_wav()          PCM WAV conversion (pydub/ffmpeg)
        │
        ├─ Sarvam STT API             text only ← transcript
        │   api.sarvam.ai/speech-to-text
        │
        ├─ ConversationManager        on-device NLU
        │   intent routing → Policy Engine / Knowledge Graph / Memory
        │
        └─ response text → browser
                │
                ▼
        POST /api/v1/voice/speak
                │
                ├─ Sarvam TTS API     audio ← WAV bytes (base64)
                │   api.sarvam.ai/text-to-speech
                │
                └─ WAV → browser Audio element → speaker
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/voice/command` | Upload audio (WAV/WebM) → Sarvam STT → policy → response |
| `POST` | `/api/v1/voice/text`    | Send text directly → policy → response (keyboard fallback) |
| `POST` | `/api/v1/voice/speak`   | Text → Sarvam TTS → WAV bytes (played in browser) |
| `GET`  | `/api/v1/voice/status`  | Current voice assistant state + conversation history |

## Configuration

```bash
# backend/.env
SARVAM_API_KEY=your_sarvam_key_here
SARVAM_OFFLINE=false          # set true to disable cloud STT/TTS
```

## Privacy

- Audio recorded in browser via `MediaRecorder` → sent to **local** backend only
- Backend sends audio (WAV, PCM) to Sarvam for transcription
- **Only text** (transcript, response) is retained in memory
- No audio files are persisted anywhere
- Conversation history stored in-memory only (not written to SQLite)

## Offline mode

When `SARVAM_OFFLINE=true` or `SARVAM_API_KEY` is not set:
- STT returns empty string + a clear status message
- TTS returns empty WAV with `X-TTS-Status: unavailable-no-api-key` header
- Text commands still work via `ConversationManager` (fully offline)

## ConversationManager intents

| Intent | Pattern example | Action |
|--------|-----------------|--------|
| `SENSOR_QUERY` | "What's the temperature?" | Reads latest sensor data |
| `MOTION_QUERY` | "Any motion detected?" | Checks motion events |
| `STATUS_QUERY` | "Is the NPU loaded?" | Queries system status |
| `ALERT_QUERY` | "Any anomaly alerts?" | Lists recent anomalies |
| `COMMAND` | "Turn on the fan" | Executes policy override |
| `GRAPH_QUERY` | "Where is my phone?" | Queries knowledge graph |
| `FEEDBACK` | "That was a false alarm" | Logs USER_CORRECTION event |
