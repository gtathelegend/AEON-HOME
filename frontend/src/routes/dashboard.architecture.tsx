import { createFileRoute } from "@tanstack/react-router";
import { ArchitecturePage } from "@/components/architecture-sections";

export const Route = createFileRoute("/dashboard/architecture")({
  head: () => ({
    meta: [
      { title: "Architecture — ÆON Home" },
      { name: "description", content: "Live system architecture visualization for every layer of the ÆON intelligence fabric." },
      { property: "og:title", content: "Architecture — ÆON Home" },
      { property: "og:description", content: "Live system architecture visualization for every layer of the ÆON intelligence fabric." },
    ],
  }),
  component: ArchitecturePage,
});
