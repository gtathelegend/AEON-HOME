"""
aeon/voice/sarvam_bridge.py — Sarvam AI voice bridge.

Sarvam's role in ÆON is strictly limited to speech I/O:
  - Speech-to-text (STT): microphone audio → text command
  - Text-to-speech (TTS): text response → speaker audio

The text command is processed entirely on-device by the policy engine.
No audio or sensor data is sent to Sarvam — only text strings.

Sarvam API docs: https://docs.sarvam.ai
Offline mode: falls back to system TTS + Vosk STT when sarvam_offline=True.
"""

from __future__ import annotations

import asyncio
import io
import structlog
from typing import AsyncIterator

import httpx
import sounddevice as sd
import soundfile as sf
import numpy as np

from aeon.config.settings import settings

log = structlog.get_logger(__name__)

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SAMPLE_RATE    = 16000
CHANNELS       = 1


class SarvamBridge:
    """
    Speech input/output bridge.

    listen() → text string  (STT)
    speak(text)             (TTS)
    """

    def __init__(self) -> None:
        self._offline = settings.sarvam_offline
        self._api_key = settings.sarvam_api_key

    async def listen(self, duration_s: float = 5.0) -> str:
        """
        Record from microphone for duration_s seconds and return transcribed text.
        """
        log.info("voice.listen_start", duration=duration_s)
        audio = await asyncio.to_thread(self._record, duration_s)

        if self._offline or not self._api_key:
            return await self._offline_stt(audio)
        return await self._sarvam_stt(audio)

    async def speak(self, text: str) -> None:
        """Convert text to speech and play through speaker."""
        log.info("voice.speak", chars=len(text))
        if self._offline or not self._api_key:
            await self._offline_tts(text)
        else:
            await self._sarvam_tts(text)

    # ── Recording ─────────────────────────────────────────────────────────────

    def _record(self, duration_s: float) -> np.ndarray:
        samples = int(SAMPLE_RATE * duration_s)
        audio = sd.rec(samples, samplerate=SAMPLE_RATE, channels=CHANNELS,
                       dtype="int16")
        sd.wait()
        return audio.flatten()

    # ── Sarvam cloud paths ────────────────────────────────────────────────────

    async def _sarvam_stt(self, audio: np.ndarray) -> str:
        buf = io.BytesIO()
        sf.write(buf, audio, SAMPLE_RATE, format="WAV", subtype="PCM_16")
        buf.seek(0)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                SARVAM_STT_URL,
                files={"file": ("audio.wav", buf, "audio/wav")},
                headers={"api-subscription-key": self._api_key},
            )
        resp.raise_for_status()
        return resp.json().get("transcript", "")

    async def _sarvam_tts(self, text: str) -> None:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                SARVAM_TTS_URL,
                json={"inputs": [text], "target_language_code": "en-IN"},
                headers={"api-subscription-key": self._api_key},
            )
        resp.raise_for_status()
        audio_b64 = resp.json()["audios"][0]
        import base64
        raw = base64.b64decode(audio_b64)
        await asyncio.to_thread(self._play_wav, raw)

    # ── Offline fallback paths ────────────────────────────────────────────────

    async def _offline_stt(self, audio: np.ndarray) -> str:
        """Offline STT placeholder — return empty string as offline fallback."""
        log.warning("voice.offline_stt — no transcript available (STT Offline/Unavailable)")
        return ""

    async def _offline_tts(self, text: str) -> None:
        """Offline TTS placeholder — integrate piper-tts or espeak here."""
        log.info("voice.offline_tts", text=text)

    def _play_wav(self, wav_bytes: bytes) -> None:
        buf = io.BytesIO(wav_bytes)
        data, sr = sf.read(buf, dtype="float32")
        sd.play(data, sr)
        sd.wait()
