import { createFileRoute } from "@tanstack/react-router";
import { VoiceAssistant } from "@/components/voice/VoiceAssistant";

export const Route = createFileRoute("/dashboard/voice")({
  head: () => ({
    meta: [
      { title: "Voice Assistant — ÆON Home" },
      {
        name: "description",
        content:
          "Talk to ÆON using Sarvam AI speech-to-text and text-to-speech. All intelligence runs on-device.",
      },
      { property: "og:title", content: "Voice Assistant — ÆON Home" },
      {
        property: "og:description",
        content: "Sarvam AI STT/TTS — on-device intelligence, zero cloud audio data.",
      },
    ],
  }),
  component: VoiceRoute,
});

function VoiceRoute() {
  return <VoiceAssistant />;
}
