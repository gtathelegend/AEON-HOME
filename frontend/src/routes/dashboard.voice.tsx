import { createFileRoute, redirect } from "@tanstack/react-router";

// Keep old bookmarks working, but use the Home page as the single voice entry point.
export const Route = createFileRoute("/dashboard/voice")({
  beforeLoad: () => {
    throw redirect({ to: "/dashboard/v2" });
  },
});
