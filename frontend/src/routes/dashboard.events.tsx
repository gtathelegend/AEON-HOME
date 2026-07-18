import { createFileRoute } from "@tanstack/react-router";
import { Events } from "@/components/dashboard-sections";

export const Route = createFileRoute("/dashboard/events")({
  head: () => ({
    meta: [
      { title: "Events — ÆON Home" },
      { name: "description", content: "Full event timeline — every signal, every decision, every moment." },
      { property: "og:title", content: "Events — ÆON Home" },
      { property: "og:description", content: "Full event timeline — every signal, every decision, every moment." },
    ],
  }),
  component: Events,
});
