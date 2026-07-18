import { createFileRoute } from "@tanstack/react-router";
import { Metrics } from "@/components/dashboard-sections";

export const Route = createFileRoute("/dashboard/metrics")({
  head: () => ({
    meta: [
      { title: "Metrics — ÆON Home" },
      { name: "description", content: "14-day history · captured on-device." },
      { property: "og:title", content: "Metrics — ÆON Home" },
      { property: "og:description", content: "14-day history · captured on-device." },
    ],
  }),
  component: Metrics,
});
