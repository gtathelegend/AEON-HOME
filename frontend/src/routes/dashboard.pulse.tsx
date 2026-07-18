import { createFileRoute } from "@tanstack/react-router";
import { Pulse } from "@/components/dashboard-sections";

export const Route = createFileRoute("/dashboard/pulse")({
  head: () => ({
    meta: [
      { title: "Persistent Pulse — ÆON Home" },
      { name: "description", content: "Heartbeat of state across power, reboot, and time." },
      { property: "og:title", content: "Persistent Pulse — ÆON Home" },
      { property: "og:description", content: "Heartbeat of state across power, reboot, and time." },
    ],
  }),
  component: Pulse,
});
