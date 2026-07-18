import { createFileRoute } from "@tanstack/react-router";
import { SelfGraph } from "@/components/dashboard-sections";

export const Route = createFileRoute("/dashboard/selfgraph")({
  head: () => ({
    meta: [
      { title: "Self Graph — ÆON Home" },
      { name: "description", content: "Your evolving profile — traced, not stored." },
      { property: "og:title", content: "Self Graph — ÆON Home" },
      { property: "og:description", content: "Your evolving profile — traced, not stored." },
    ],
  }),
  component: SelfGraph,
});
