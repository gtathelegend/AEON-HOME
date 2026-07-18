import { createFileRoute } from "@tanstack/react-router";
import { Sensors } from "@/components/dashboard-sections";

export const Route = createFileRoute("/dashboard/sensors")({
  head: () => ({
    meta: [
      { title: "Sensors — ÆON Home" },
      { name: "description", content: "Live environmental data — temperature, humidity, motion, and more." },
      { property: "og:title", content: "Sensors — ÆON Home" },
      { property: "og:description", content: "Live environmental data — temperature, humidity, motion, and more." },
    ],
  }),
  component: Sensors,
});
