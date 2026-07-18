import { createFileRoute } from "@tanstack/react-router";
import { Onboarding } from "@/components/dashboard-sections";

export const Route = createFileRoute("/dashboard/onboarding")({
  component: OnboardingRoute,
});

function OnboardingRoute() {
  return <Onboarding />;
}
