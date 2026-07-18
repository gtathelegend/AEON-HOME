/**
 * SarvamBridge.ts
 *
 * Browser-side Sarvam AI bridge utilities:
 *   - sarvamSTT()  — POST audio Blob → /api/v1/voice/command → transcript + response
 *   - sarvamTTS()  — POST text → /api/v1/voice/speak → plays WAV in browser
 *   - voiceStatus() — GET /api/v1/voice/status
 *
 * These are thin wrappers around the backend API — no audio ever reaches Sarvam
 * directly from the browser; all processing is routed through the edge server.
 */

const BASE =
  (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_API_BASE_URL) ||
  "http://localhost:8000";

export interface VoiceCommandResult {
  transcript: string;
  response: string;
}

export interface VoiceStatusResult {
  sarvam_api_key_set: boolean;
  offline_mode: boolean;
  sarvam_connected: boolean;
  history: Array<{ role: string; content: string }>;
}

/**
 * sarvamSTT — send a recorded audio Blob to the backend Sarvam STT endpoint.
 * The backend converts audio → WAV if needed, sends to Sarvam, and returns
 * the transcript + policy-engine response.
 */
export async function sarvamSTT(
  audioBlob: Blob,
  filename = "recording.webm",
): Promise<VoiceCommandResult> {
  const form = new FormData();
  form.append("file", audioBlob, filename);

  const res = await fetch(`${BASE}/api/v1/voice/command`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    throw new Error(`Sarvam STT failed: HTTP ${res.status}`);
  }

  return res.json() as Promise<VoiceCommandResult>;
}

/**
 * sarvamTTS — send text to the backend Sarvam TTS endpoint.
 * Returns an AudioBuffer URL that can be fed into an <audio> element.
 * Returns null if TTS is unavailable (no API key / offline).
 */
export async function sarvamTTS(text: string, language = "en-IN"): Promise<string | null> {
  const res = await fetch(`${BASE}/api/v1/voice/speak`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language }),
  });

  if (!res.ok) return null;

  // If backend signals TTS unavailable via header, skip
  const status = res.headers.get("X-TTS-Status");
  if (status) return null;

  const blob = await res.blob();
  if (blob.size === 0) return null;

  return URL.createObjectURL(blob);
}

/**
 * playTTS — convenience wrapper that calls sarvamTTS and plays the result.
 * Cleans up the object URL automatically when playback ends.
 */
export async function playTTS(text: string, language = "en-IN"): Promise<void> {
  const url = await sarvamTTS(text, language);
  if (!url) return;

  const audio = new Audio(url);
  audio.onended = () => URL.revokeObjectURL(url);
  audio.onerror = () => URL.revokeObjectURL(url);
  await audio.play();
}

/**
 * voiceStatus — fetch current voice assistant status from the backend.
 */
export async function voiceStatus(): Promise<VoiceStatusResult> {
  const res = await fetch(`${BASE}/api/v1/voice/status`);
  if (!res.ok) throw new Error(`Voice status failed: HTTP ${res.status}`);
  return res.json() as Promise<VoiceStatusResult>;
}

/**
 * sendTextCommand — POST plain text to /api/v1/voice/text (keyboard / fallback mode).
 */
export async function sendTextCommand(
  text: string,
  userId = "default_user",
): Promise<VoiceCommandResult> {
  const res = await fetch(`${BASE}/api/v1/voice/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, user_id: userId }),
  });
  if (!res.ok) throw new Error(`Text command failed: HTTP ${res.status}`);
  return res.json() as Promise<VoiceCommandResult>;
}
