import { createFileRoute } from "@tanstack/react-router";
import { Dream } from "@/components/dashboard-sections";

export const Route = createFileRoute("/dashboard/dream")({
  head: () => ({
    meta: [
      { title: "Dream State — ÆON Home" },
      { name: "description", content: "At night, ÆON replays the day and gets smaller, faster, sharper." },
      { property: "og:title", content: "Dream State — ÆON Home" },
      { property: "og:description", content: "At night, ÆON replays the day and gets smaller, faster, sharper." },
    ],
  }),
  component: Dream,
});
