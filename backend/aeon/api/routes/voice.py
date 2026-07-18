"""
POST /api/v1/voice/command   — transcribe an audio upload (WAV or WebM) and run as a command
POST /api/v1/voice/speak     — synthesise text to speech (returns WAV bytes)
POST /api/v1/voice/text      — process text directly and return a text response
GET  /api/v1/voice/status    — current voice assistant status
"""
from __future__ import annotations

import io
import logging
from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter(tags=["voice"])
log = logging.getLogger(__name__)


class SpeakRequest(BaseModel):
    text: str
    language: str = "en-IN"


class TextCommandRequest(BaseModel):
    text: str
    user_id: str = "default_user"


def _convert_to_wav(raw: bytes, content_type: str) -> bytes:
    """
    Convert audio bytes to PCM WAV if not already WAV.
    Accepts: audio/wav, audio/wave, audio/webm, audio/ogg, audio/mp4, audio/mpeg.
    Returns WAV bytes suitable for soundfile.read() or Sarvam STT.
    Requires ffmpeg to be installed for non-WAV formats.
    """
    wav_types = {"audio/wav", "audio/wave", "audio/x-wav"}
    if content_type.split(";")[0].strip().lower() in wav_types:
        return raw   # already WAV

    # Try pydub (needs ffmpeg) for webm/ogg/mp4
    try:
        from pydub import AudioSegment  # type: ignore[import]
        fmt = "webm" if "webm" in content_type else "ogg"
        seg = AudioSegment.from_file(io.BytesIO(raw), format=fmt)
        seg = seg.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        buf = io.BytesIO()
        seg.export(buf, format="wav")
        return buf.getvalue()
    except Exception as exc:
        log.warning("voice.convert_failed — falling back to raw bytes: %s", exc)
        return raw   # return as-is; Sarvam may still accept it


@router.post("/voice/command")
async def voice_command(
    request: Request,
    file: UploadFile = File(...),
):
    """
    Accept an audio upload (WAV or WebM), transcribe via Sarvam STT,
    and dispatch to ConversationManager.
    Returns the transcription and response text.
    """
    from aeon_platform.filesystem.settings import settings

    raw = await file.read()
    content_type = file.content_type or "audio/wav"

    # Publish "transcribing" status to all WS clients
    ws_bus = request.app.state.ws_bus
    await ws_bus.publish("voice_status", {"state": "transcribing"})

    transcript = ""

    if settings.sarvam_api_key and not settings.sarvam_offline:
        # Convert to WAV for Sarvam (which expects PCM WAV)
        wav_bytes = await __import__("asyncio").to_thread(
            _convert_to_wav, raw, content_type
        )
        try:
            import httpx
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    "https://api.sarvam.ai/speech-to-text",
                    files={"file": ("audio.wav", wav_bytes, "audio/wav")},
                    headers={"api-subscription-key": settings.sarvam_api_key},
                )
            if resp.is_success:
                transcript = resp.json().get("transcript", "")
            else:
                log.warning("voice.sarvam_stt_error status=%s", resp.status_code)
                await ws_bus.publish("voice_status", {
                    "state": "error",
                    "error": f"Sarvam STT returned {resp.status_code}",
                })
                return {"transcript": "", "response": "Speech recognition failed. Please try again."}
        except Exception as exc:
            log.exception("voice.sarvam_stt_exception")
            await ws_bus.publish("voice_status", {"state": "error", "error": str(exc)})
            return {"transcript": "", "response": "Network error reaching Sarvam API."}
    else:
        # Offline / no key — return a clear status rather than pretending
        transcript = ""
        reason = "Sarvam Voice Service Unavailable"
        if settings.sarvam_offline:
            reason = "Sarvam Voice Service is Offline"
        elif not settings.sarvam_api_key:
            reason = "Sarvam API key not configured. Set SARVAM_API_KEY in backend/.env"

        await ws_bus.publish("voice_status", {
            "state": "error",
            "error": reason,
        })
        return {
            "transcript": "",
            "response": reason,
        }

    if not transcript.strip():
        await ws_bus.publish("voice_status", {"state": "idle", "last_query": ""})
        return {"transcript": "", "response": "No speech detected in audio."}

    # Process through ConversationManager
    await ws_bus.publish("voice_status", {
        "state": "processing",
        "last_query": transcript,
    })
    conv_mgr = request.app.state.voice_manager
    response_text = await conv_mgr.handle_utterance(transcript)

    await ws_bus.publish("voice_status", {
        "state": "idle",
        "last_query": transcript,
        "last_response": response_text,
    })
    return {"transcript": transcript, "response": response_text}


@router.post("/voice/text")
async def text_command(body: TextCommandRequest, request: Request):
    """
    Process text directly through ConversationManager.
    Works when microphone is unavailable or for text-mode testing.
    """
    ws_bus = request.app.state.ws_bus
    await ws_bus.publish("voice_status", {
        "state": "processing",
        "last_query": body.text,
    })

    conv_mgr = request.app.state.voice_manager
    response_text = await conv_mgr.handle_utterance(body.text, user_id=body.user_id)

    await ws_bus.publish("voice_status", {
        "state": "idle",
        "last_query": body.text,
        "last_response": response_text,
    })
    return {"transcript": body.text, "response": response_text}


@router.post("/voice/speak")
async def voice_speak(body: SpeakRequest, request: Request):
    """
    Convert text to speech via Sarvam TTS and return WAV bytes.
    Audio is played locally by the PWA — never stored externally.
    """
    from aeon_platform.filesystem.settings import settings

    if not settings.sarvam_api_key or settings.sarvam_offline:
        # Return empty WAV with a clear Content header so client knows
        return Response(
            content=b"",
            media_type="audio/wav",
            headers={"X-TTS-Status": "unavailable-no-api-key"},
        )

    try:
        import httpx, base64
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.sarvam.ai/text-to-speech",
                json={"inputs": [body.text], "target_language_code": body.language},
                headers={"api-subscription-key": settings.sarvam_api_key},
            )
        if not resp.is_success:
            log.warning("voice.sarvam_tts_error status=%s", resp.status_code)
            return Response(content=b"", media_type="audio/wav",
                            headers={"X-TTS-Status": f"sarvam-error-{resp.status_code}"})
        wav = base64.b64decode(resp.json()["audios"][0])
        return Response(content=wav, media_type="audio/wav")
    except Exception as exc:
        log.exception("voice.sarvam_tts_exception")
        return Response(content=b"", media_type="audio/wav",
                        headers={"X-TTS-Status": "network-error"})


@router.get("/voice/status")
async def voice_status(request: Request):
    """Current voice assistant state."""
    from aeon_platform.filesystem.settings import settings
    conv_mgr = request.app.state.voice_manager
    return {
        "sarvam_api_key_set": bool(settings.sarvam_api_key),
        "offline_mode":       settings.sarvam_offline,
        "sarvam_connected":   bool(settings.sarvam_api_key) and not settings.sarvam_offline,
        "history":            conv_mgr.get_history() if conv_mgr else [],
    }
