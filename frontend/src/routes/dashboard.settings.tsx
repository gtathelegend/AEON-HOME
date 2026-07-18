import { createFileRoute } from "@tanstack/react-router";
import { SettingsPage } from "@/components/dashboard-sections";

export const Route = createFileRoute("/dashboard/settings")({
  head: () => ({
    meta: [
      { title: "Settings — ÆON Home" },
      { name: "description", content: "Tune the fabric. It stays local, always." },
      { property: "og:title", content: "Settings — ÆON Home" },
      { property: "og:description", content: "Tune the fabric. It stays local, always." },
    ],
  }),
  component: SettingsPage,
});
