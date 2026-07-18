import { createFileRoute } from "@tanstack/react-router";
import { SnapdragonStatusSection } from "@/components/dashboard-sections";

export const Route = createFileRoute("/dashboard/npu")({
  component: NpuRoute,
});

function NpuRoute() {
  return <SnapdragonStatusSection />;
}
