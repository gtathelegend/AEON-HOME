import { createFileRoute } from "@tanstack/react-router";
import { Alerts } from "@/components/dashboard-sections";

export const Route = createFileRoute("/dashboard/alerts")({
  head: () => ({
    meta: [
      { title: "Alerts — ÆON Home" },
      { name: "description", content: "Signed capability alerts — every one is auditable." },
      { property: "og:title", content: "Alerts — ÆON Home" },
      { property: "og:description", content: "Signed capability alerts — every one is auditable." },
    ],
  }),
  component: Alerts,
});
