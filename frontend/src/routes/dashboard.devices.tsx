import { createFileRoute } from "@tanstack/react-router";
import { Devices } from "@/components/dashboard-sections";

export const Route = createFileRoute("/dashboard/devices")({
  head: () => ({
    meta: [
      { title: "Devices — ÆON Home" },
      { name: "description", content: "Every node in your ÆON mesh — local-first, always." },
      { property: "og:title", content: "Devices — ÆON Home" },
      { property: "og:description", content: "Every node in your ÆON mesh — local-first, always." },
    ],
  }),
  component: Devices,
});
