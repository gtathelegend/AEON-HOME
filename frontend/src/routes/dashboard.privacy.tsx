import { createFileRoute } from "@tanstack/react-router";
import { Privacy } from "@/components/dashboard-sections";

export const Route = createFileRoute("/dashboard/privacy")({
  head: () => ({
    meta: [
      { title: "Privacy Audit — ÆON Home" },
      { name: "description", content: "Zero raw data leaves the mesh. Everything is a signed intention." },
      { property: "og:title", content: "Privacy Audit — ÆON Home" },
      { property: "og:description", content: "Zero raw data leaves the mesh. Everything is a signed intention." },
    ],
  }),
  component: Privacy,
});
