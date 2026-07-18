import { createFileRoute } from "@tanstack/react-router";
import { Migration } from "@/components/dashboard-sections";

export const Route = createFileRoute("/dashboard/migration")({
  head: () => ({
    meta: [
      { title: "Migration — ÆON Home" },
      { name: "description", content: "Move your ÆON identity to a new device. Seamlessly." },
      { property: "og:title", content: "Migration — ÆON Home" },
      { property: "og:description", content: "Move your ÆON identity to a new device. Seamlessly." },
    ],
  }),
  component: Migration,
});
