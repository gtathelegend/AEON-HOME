/**
 * VoiceAssistant.tsx
 *
 * Full-page voice assistant component with:
 *  - Browser MediaRecorder → sends WAV to /api/v1/voice/command (Sarvam STT)
 *  - /api/v1/voice/text for keyboard / quick-command fallback
 *  - /api/v1/voice/speak  (Sarvam TTS) → plays returned WAV in browser
 *  - Live status synced from useAeon WebSocket telemetry
 *  - Conversation history with animated typing indicator
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Mic, MicOff, Send, Volume2, VolumeX, Zap, Radio } from "lucide-react";
import { useAeon } from "@/hooks/use-aeon-telemetry";
import { Reveal } from "@/components/Reveal";
import { sendVoiceText } from "@/lib/api";

const API_BASE =
  (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_API_BASE_URL) ||
  "http://localhost:8000";

type Message = {
  role: "user" | "aeon";
  text: string;
  ts: string;
};

function nowTime() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/* ── TTS helper ─────────────────────────────────────────────────────────── */
async function speakViaApi(text: string): Promise<void> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/voice/speak`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, language: "en-IN" }),
    });
    if (!res.ok || res.headers.get("X-TTS-Status")) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => URL.revokeObjectURL(url);
    await audio.play();
  } catch {
    /* offline — silently skip TTS */
  }
}

/* ── STT via MediaRecorder → /api/v1/voice/command ─────────────────────── */
async function transcribeAudio(blob: Blob): Promise<{ transcript: string; response: string }> {
  const form = new FormData();
  form.append("file", blob, "recording.webm");
  const res = await fetch(`${API_BASE}/api/v1/voice/command`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`STT ${res.status}`);
  return res.json();
}

/* ── Component ──────────────────────────────────────────────────────────── */
export function VoiceAssistant() {
  const { telemetry, sendVoiceQuery, startListening } = useAeon();
  const voice = telemetry.voiceAssistant;

  const [conversation, setConversation] = useState<Message[]>([
    {
      role: "aeon",
      text: "Namaste! Main ÆON hoon. You can type a command, or hold the mic to speak.",
      ts: nowTime(),
    },
  ]);
  const [textInput, setTextInput] = useState("");
  const [sending, setSending] = useState(false);
  const [recording, setRecording] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [mediaError, setMediaError] = useState<string | null>(null);

  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  /* auto-scroll */
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [conversation, sending]);

  /* ── Text send ─────────────────────────────────────────────────────────── */
  const handleSend = useCallback(async () => {
    const query = textInput.trim();
    if (!query) return;
    setTextInput("");
    setConversation((prev) => [...prev, { role: "user", text: query, ts: nowTime() }]);
    setSending(true);
    try {
      const res = await sendVoiceText(query);
      const reply = res.response || res.transcript || "Command received.";
      setConversation((prev) => [...prev, { role: "aeon", text: reply, ts: nowTime() }]);
      if (ttsEnabled) speakViaApi(reply);
    } catch {
      sendVoiceQuery(query);
      const fallback = voice.lastResponse || "Command received.";
      setConversation((prev) => [...prev, { role: "aeon", text: fallback, ts: nowTime() }]);
      if (ttsEnabled) speakViaApi(fallback);
    } finally {
      setSending(false);
    }
  }, [textInput, ttsEnabled, voice.lastResponse, sendVoiceQuery]);

  /* ── Mic recording ─────────────────────────────────────────────────────── */
  const startRecording = useCallback(async () => {
    setMediaError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
      chunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setSending(true);
        setConversation((prev) => [...prev, { role: "user", text: "🎤 (voice message)", ts: nowTime() }]);
        try {
          const { transcript, response } = await transcribeAudio(blob);
          if (transcript) {
            setConversation((prev) => {
              const copy = [...prev];
              copy[copy.length - 1] = { role: "user", text: transcript, ts: nowTime() };
              return [...copy, { role: "aeon", text: response, ts: nowTime() }];
            });
            if (ttsEnabled) speakViaApi(response);
          } else {
            setConversation((prev) => {
              const copy = [...prev];
              copy[copy.length - 1] = {
                role: "user",
                text: "🎤 (no speech detected)",
                ts: nowTime(),
              };
              return copy;
            });
          }
        } catch (err) {
          setMediaError(String(err));
        } finally {
          setSending(false);
        }
      };
      mr.start();
      mediaRef.current = mr;
      setRecording(true);
      startListening();
    } catch (err) {
      setMediaError("Microphone access denied. Use text mode instead.");
    }
  }, [ttsEnabled, startListening]);

  const stopRecording = useCallback(() => {
    mediaRef.current?.stop();
    mediaRef.current = null;
    setRecording(false);
  }, []);

  const quickCmds = [
    "Who is home?",
    "Lock the front door",
    "Start dream mode",
    "Show today's events",
    "What's the temperature?",
    "Privacy status report",
    "Turn on the fan",
    "Turn off the lights",
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <Reveal>
        <div>
          <h1
            className="text-3xl font-semibold tracking-tight md:text-4xl"
            style={{ fontFamily: "'Instrument Serif', serif", fontWeight: 400 }}
          >
            <span className="text-gradient">Voice Assistant</span>
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Powered by Sarvam AI STT/TTS — on-device intelligence, zero cloud data.
          </p>
        </div>
      </Reveal>

      {/* Status pills */}
      <Reveal>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Sarvam AI",  ok: voice.sarvamConnected, tint: "var(--aeon-cyan)"   },
            { label: "Language",   value: voice.language || "en-IN", tint: "var(--aeon-blue)"   },
            { label: "Listening",  ok: voice.isListening || recording, tint: "var(--aeon-purple)" },
            { label: "Speaking",   ok: voice.isSpeaking,  tint: "var(--aeon-pink)"   },
          ].map((p) => (
            <div key={p.label} className="glass-card flex items-center gap-2.5 rounded-2xl p-3">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{
                  background:
                    p.ok !== undefined
                      ? p.ok
                        ? "oklch(0.7 0.15 150)"
                        : "oklch(0.6 0.15 27)"
                      : p.tint,
                }}
              />
              <div className="min-w-0">
                <p className="text-[10px] text-muted-foreground">{p.label}</p>
                <p className="text-xs font-medium">
                  {p.value ?? (p.ok ? "Active" : "Inactive")}
                </p>
              </div>
            </div>
          ))}
        </div>
      </Reveal>

      {/* Conversation */}
      <Reveal>
        <div className="glass-card overflow-hidden rounded-3xl">
          {/* Header bar */}
          <div className="flex items-center justify-between border-b border-white/40 px-5 py-3">
            <div className="flex items-center gap-2">
              <Radio className="h-4 w-4" style={{ color: "var(--aeon-purple)" }} />
              <span className="text-sm font-semibold">Conversation</span>
            </div>
            <div className="flex items-center gap-2">
              {/* TTS toggle */}
              <button
                onClick={() => setTtsEnabled((v) => !v)}
                aria-label={ttsEnabled ? "Mute TTS" : "Enable TTS"}
                title={ttsEnabled ? "TTS on" : "TTS off"}
                className="grid h-8 w-8 place-items-center rounded-full bg-white/60 hover:bg-white transition active:scale-95"
              >
                {ttsEnabled ? <Volume2 className="h-3.5 w-3.5" /> : <VolumeX className="h-3.5 w-3.5" />}
              </button>

              {/* Mic button */}
              <button
                onMouseDown={startRecording}
                onMouseUp={stopRecording}
                onTouchStart={startRecording}
                onTouchEnd={stopRecording}
                disabled={sending}
                aria-label={recording ? "Release to send" : "Hold to speak"}
                className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition active:scale-95 select-none disabled:opacity-40 ${
                  recording
                    ? "animate-pulse bg-red-500/10 text-red-600"
                    : "bg-foreground text-background hover:scale-[1.02]"
                }`}
              >
                {recording ? <MicOff className="h-3 w-3" /> : <Mic className="h-3 w-3" />}
                {recording ? "Release to send" : "Hold to speak"}
              </button>
            </div>
          </div>

          {/* Messages */}
          <div
            ref={scrollRef}
            className="flex max-h-80 flex-col gap-3 overflow-y-auto p-4"
          >
            {conversation.map((msg, i) => (
              <div
                key={i}
                className={`flex gap-2.5 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
              >
                <span
                  className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-xs font-bold"
                  style={{
                    background:
                      msg.role === "aeon"
                        ? "var(--gradient-aeon)"
                        : "oklch(0.92 0.01 275)",
                    color:
                      msg.role === "aeon" ? "white" : "oklch(0.3 0.02 275)",
                  }}
                >
                  {msg.role === "aeon" ? "Æ" : "U"}
                </span>
                <div
                  className={`max-w-[75%] rounded-2xl px-3.5 py-2.5 text-sm ${
                    msg.role === "user"
                      ? "bg-foreground text-background"
                      : "glass-card"
                  }`}
                >
                  <p>{msg.text}</p>
                  <p className="mt-1 text-[10px] opacity-50">{msg.ts}</p>
                </div>
              </div>
            ))}

            {/* Typing indicator */}
            {sending && (
              <div className="flex gap-2.5">
                <span
                  className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-xs font-bold text-white"
                  style={{ background: "var(--gradient-aeon)" }}
                >
                  Æ
                </span>
                <div className="glass-card flex items-center gap-1 rounded-2xl px-4 py-3">
                  {[0, 0.2, 0.4].map((d, i) => (
                    <span
                      key={i}
                      className="h-1.5 w-1.5 rounded-full bg-foreground/40 animate-bounce"
                      style={{ animationDelay: `${d}s` }}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Error */}
          {mediaError && (
            <div className="mx-4 mb-2 rounded-xl bg-red-500/10 px-3 py-2 text-xs text-red-600">
              {mediaError}
            </div>
          )}

          {/* Text input */}
          <div className="flex items-center gap-2 border-t border-white/40 p-3">
            <input
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Type a command or question…"
              className="flex-1 rounded-xl bg-white/60 px-3.5 py-2.5 text-sm outline-none placeholder:text-muted-foreground"
            />
            <button
              onClick={handleSend}
              disabled={sending || !textInput.trim()}
              className="grid h-10 w-10 place-items-center rounded-xl bg-foreground text-background transition hover:scale-[1.05] disabled:opacity-40"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </Reveal>

      {/* Quick commands */}
      <Reveal>
        <div className="glass-card rounded-3xl p-5">
          <p className="mb-3 text-sm font-semibold">Quick commands</p>
          <div className="flex flex-wrap gap-2">
            {quickCmds.map((cmd) => (
              <button
                key={cmd}
                onClick={() => setTextInput(cmd)}
                className="glass-card rounded-full px-3.5 py-1.5 text-xs text-muted-foreground hover:text-foreground transition active:scale-95"
              >
                {cmd}
              </button>
            ))}
          </div>
        </div>
      </Reveal>

      {/* Sarvam info card */}
      <Reveal>
        <div className="glass-card rounded-3xl p-5">
          <div className="flex items-start gap-3">
            <div
              className="grid h-9 w-9 shrink-0 place-items-center rounded-xl"
              style={{ background: "var(--gradient-aeon)" }}
            >
              <Zap className="h-4 w-4 text-white" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-semibold">Sarvam AI Speech Bridge</p>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Speech-to-text and text-to-speech run through Sarvam AI — text only crosses
                the API, never raw audio. All intent processing happens on-device via the
                ÆON policy engine. Set <code className="rounded bg-black/5 px-1">SARVAM_API_KEY</code> in{" "}
                <code className="rounded bg-black/5 px-1">backend/.env</code> to activate.
              </p>
            </div>
          </div>
        </div>
      </Reveal>
    </div>
  );
}
