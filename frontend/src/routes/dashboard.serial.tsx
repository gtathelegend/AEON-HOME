import { createFileRoute } from "@tanstack/react-router";
import { SerialStatusSection } from "@/components/dashboard-sections";

export const Route = createFileRoute("/dashboard/serial")({
  component: SerialRoute,
});

function SerialRoute() {
  return <SerialStatusSection />;
}
