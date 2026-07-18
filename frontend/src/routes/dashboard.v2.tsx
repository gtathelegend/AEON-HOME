import { createFileRoute } from "@tanstack/react-router";
import { DashboardV2 } from "@/components/dashboard-sections";

export const Route = createFileRoute("/dashboard/v2")({
  head: () => ({
    meta: [
      { title: "Dashboard V2 — ÆON Home" },
      { name: "description", content: "Single-page ÆON Home dashboard with every section, no duplicates." },
      { property: "og:title", content: "Dashboard V2 — ÆON Home" },
      { property: "og:description", content: "Every ÆON section in one page." },
    ],
  }),
  component: DashboardV2,
});
