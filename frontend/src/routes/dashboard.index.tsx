import { createFileRoute } from "@tanstack/react-router";
import { Overview } from "@/components/dashboard-sections";

export const Route = createFileRoute("/dashboard/")({
  head: () => ({
    meta: [
      { title: "Overview — ÆON Home" },
      { name: "description", content: "Live overview of your ÆON Home intelligence fabric." },
      { property: "og:title", content: "Overview — ÆON Home" },
      { property: "og:description", content: "Live overview of your ÆON Home intelligence fabric." },
    ],
  }),
  component: Overview,
});
