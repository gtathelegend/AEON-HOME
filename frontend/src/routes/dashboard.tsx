import { createFileRoute, Link, Outlet, useRouterState } from "@tanstack/react-router";
import { useState } from "react";
import {
  Home,
  LayoutDashboard,
  Radio,
  Bell,
  Lock,
  Network,
  Moon,
  Search,
  Wifi,
  ShieldCheck,
  ChevronRight,
  ArrowLeft,
  Menu,
  X,
  Thermometer,
  Waypoints,
  Layers,
  Activity,
  Cpu,
  Sparkles,
  Zap,
} from "lucide-react";
import { AeonTelemetryProvider } from "@/hooks/use-aeon-telemetry";
import { AEON_LOGO_SRC } from "@/lib/brand";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "ÆON Home — Live Dashboard" },
      { name: "description", content: "Command center for the ÆON persistent intelligence fabric across every device in your home." },
      { property: "og:title", content: "ÆON Home — Live Dashboard" },
      { property: "og:description", content: "Command center for the ÆON persistent intelligence fabric." },
    ],
  }),
  component: DashboardLayout,
});

type NavItem = {
  to: "/dashboard" | "/dashboard/v2" | "/dashboard/devices" | "/dashboard/alerts" | "/dashboard/pulse" | "/dashboard/privacy" | "/dashboard/selfgraph" | "/dashboard/dream" | "/dashboard/metrics" | "/dashboard/settings" | "/dashboard/events" | "/dashboard/sensors" | "/dashboard/migration" | "/dashboard/onboarding" | "/dashboard/serial" | "/dashboard/npu" | "/dashboard/architecture";
  label: string;
  icon: typeof Home;
};

const NAV: NavItem[] = [
  { to: "/dashboard/v2",         label: "Home",       icon: Home },
  { to: "/dashboard",            label: "Overview",   icon: LayoutDashboard },
  { to: "/dashboard/onboarding", label: "Onboarding", icon: Sparkles },
  { to: "/dashboard/serial",     label: "Serial",     icon: Cpu },
  { to: "/dashboard/npu",        label: "NPU Engine", icon: Zap },
  { to: "/dashboard/devices",    label: "Devices",    icon: Radio },
  { to: "/dashboard/alerts",     label: "Alerts",     icon: Bell },
  { to: "/dashboard/sensors",    label: "Sensors",    icon: Thermometer },
  { to: "/dashboard/events",     label: "Events",     icon: Activity },
  { to: "/dashboard/selfgraph",  label: "Self Graph", icon: Network },
  { to: "/dashboard/dream",      label: "Dream",      icon: Moon },
  { to: "/dashboard/privacy",    label: "Privacy",    icon: Lock },
  { to: "/dashboard/migration",  label: "Migration",     icon: Waypoints },
  { to: "/dashboard/architecture", label: "Architecture", icon: Layers },
];

function DashboardLayout() {
  const [mobileMoreOpen, setMobileMoreOpen] = useState(false);
  const [desktopMenuOpen, setDesktopMenuOpen] = useState(false);
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const normalized = pathname.replace(/\/$/, "") || "/dashboard";
  const current = NAV.find((n) => n.to === normalized) ?? NAV[0];

  // Primary tabs shown in bottom bar; the rest go in "More"
  const primaryTabs = NAV.slice(0, 4);
  const moreTabs = NAV.slice(4);
  const isMoreActive = moreTabs.some((n) => n.to === normalized);

  return (
    <AeonTelemetryProvider>
      <div className="relative min-h-screen overflow-x-hidden bg-background text-foreground">
        <AmbientGlow />

        {/* Desktop navbar with hamburger menu */}
        <Navbar
          current={normalized}
          menuOpen={desktopMenuOpen}
          onMenuToggle={() => setDesktopMenuOpen((v) => !v)}
          onMenuClose={() => setDesktopMenuOpen(false)}
        />

        {/* Mobile app-style header */}
        <header
          className="glass-card sticky top-0 z-40 flex items-center justify-between gap-2 rounded-none border-b border-white/40 px-4 py-3 lg:hidden"
          style={{ paddingTop: "max(0.75rem, env(safe-area-inset-top))" }}
        >
          <Link to="/" className="flex min-w-0 items-center gap-2">
            <img src={AEON_LOGO_SRC} alt="ÆON" className="h-7 w-7 shrink-0 object-contain" />
            <div className="min-w-0">
              <p className="truncate text-[15px] font-semibold leading-tight tracking-tight">{current.label}</p>
              <p className="truncate text-[11px] leading-tight text-muted-foreground">ÆON Home</p>
            </div>
          </Link>
          <div className="flex shrink-0 items-center gap-1.5">
            <button aria-label="Search" className="grid h-9 w-9 place-items-center rounded-full bg-white/60 hover:bg-white active:scale-95 transition">
              <Search className="h-4 w-4" />
            </button>
            <Link to="/dashboard/alerts" aria-label="Notifications" className="relative grid h-9 w-9 place-items-center rounded-full bg-white/60 hover:bg-white active:scale-95 transition">
              <Bell className="h-4 w-4" />
              <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full" style={{ background: "var(--aeon-purple)", boxShadow: "0 0 8px var(--aeon-purple)" }} />
            </Link>
          </div>
        </header>

        {/* Mobile "More" sheet */}
        {mobileMoreOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <div
              className="absolute inset-0 bg-foreground/30 backdrop-blur-sm animate-in fade-in"
              onClick={() => setMobileMoreOpen(false)}
            />
            <div
              className="glass-card absolute inset-x-0 bottom-0 rounded-t-3xl p-4 pb-6 animate-in slide-in-from-bottom"
              style={{ paddingBottom: "max(1.5rem, env(safe-area-inset-bottom))" }}
            >
              <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-foreground/15" />
              <div className="mb-3 flex items-center justify-between">
                <p className="text-sm font-semibold">More</p>
                <button onClick={() => setMobileMoreOpen(false)} aria-label="Close" className="grid h-8 w-8 place-items-center rounded-full bg-white/60">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {moreTabs.map((item) => {
                  const Icon = item.icon;
                  const isActive = item.to === normalized;
                  return (
                    <Link
                      key={item.to}
                      to={item.to}
                      onClick={() => setMobileMoreOpen(false)}
                      className={`flex flex-col items-center gap-1.5 rounded-2xl px-2 py-3 text-center text-xs transition active:scale-95 ${
                        isActive ? "bg-foreground/5 font-medium" : "bg-white/50 text-muted-foreground hover:bg-white"
                      }`}
                    >
                      <Icon className="h-5 w-5" />
                      <span className="truncate">{item.label}</span>
                    </Link>
                  );
                })}
                <Link
                  to="/"
                  onClick={() => setMobileMoreOpen(false)}
                  className="flex flex-col items-center gap-1.5 rounded-2xl bg-white/50 px-2 py-3 text-center text-xs text-muted-foreground transition hover:bg-white active:scale-95"
                >
                  <ArrowLeft className="h-5 w-5" />
                  <span className="truncate">Back to site</span>
                </Link>
              </div>
            </div>
          </div>
        )}

        <div className="mx-auto flex min-h-screen w-full max-w-[1400px] flex-col gap-4 p-0 sm:gap-6 sm:p-4 lg:h-screen lg:px-6 lg:pb-6 lg:pt-3">
          <main
            className="flex-1 px-3 pb-28 pt-3 sm:px-4 sm:pt-0 sm:pb-6 lg:overflow-y-auto lg:pr-1 lg:pb-0 lg:pt-0"
            style={{ paddingBottom: "max(7rem, calc(env(safe-area-inset-bottom) + 6rem))" }}
          >
            <Outlet />
          </main>
        </div>

        {/* Mobile bottom tab bar */}
        <nav
          className="fixed inset-x-0 bottom-0 z-40 lg:hidden"
          style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
        >
          <div className="glass-card mx-3 mb-3 grid grid-cols-5 items-stretch gap-1 rounded-3xl px-2 py-2 shadow-lg">
            {primaryTabs.map((item) => {
              const Icon = item.icon;
              const isActive = item.to === normalized;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`relative flex flex-col items-center justify-center gap-0.5 rounded-2xl px-1 py-1.5 text-[10px] transition active:scale-95 ${
                    isActive ? "font-semibold text-foreground" : "text-muted-foreground"
                  }`}
                >
                  {isActive && (
                    <span
                      className="absolute inset-0 -z-10 rounded-2xl"
                      style={{ background: "color-mix(in oklab, var(--aeon-purple) 12%, white)" }}
                    />
                  )}
                  <Icon className="h-[18px] w-[18px]" />
                  <span className="truncate leading-tight">{item.label}</span>
                </Link>
              );
            })}
            <button
              onClick={() => setMobileMoreOpen(true)}
              className={`relative flex flex-col items-center justify-center gap-0.5 rounded-2xl px-1 py-1.5 text-[10px] transition active:scale-95 ${
                isMoreActive ? "font-semibold text-foreground" : "text-muted-foreground"
              }`}
            >
              {isMoreActive && (
                <span
                  className="absolute inset-0 -z-10 rounded-2xl"
                  style={{ background: "color-mix(in oklab, var(--aeon-purple) 12%, white)" }}
                />
              )}
              <Menu className="h-[18px] w-[18px]" />
              <span className="truncate leading-tight">More</span>
            </button>
          </div>
        </nav>
      </div>
    </AeonTelemetryProvider>
  );
}

function AmbientGlow() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute inset-0 opacity-70" style={{ background: "var(--gradient-soft)" }} />
      <div
        className="absolute -top-40 left-1/2 h-[600px] w-[900px] -translate-x-1/2 rounded-full opacity-40 blur-3xl animate-drift"
        style={{ background: "var(--gradient-aeon)" }}
      />
      <div
        className="absolute inset-0 opacity-[0.035]"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, oklch(0.16 0.02 275) 1px, transparent 0)",
          backgroundSize: "28px 28px",
        }}
      />
    </div>
  );
}

function Navbar({
  current,
  menuOpen,
  onMenuToggle,
  onMenuClose,
}: {
  current: string;
  menuOpen: boolean;
  onMenuToggle: () => void;
  onMenuClose: () => void;
}) {
  const currentItem = NAV.find((n) => n.to === current);
  const CurrentIcon = currentItem?.icon ?? LayoutDashboard;

  return (
    <>
      {/* ── Top bar ── */}
      <header className="glass-card sticky top-0 z-40 hidden lg:flex items-center justify-between gap-4 rounded-none border-b border-white/40 px-6 py-3">
        {/* Left: logo + hamburger */}
        <div className="flex items-center gap-3">
          <Link to="/" className="flex min-w-0 items-center gap-2.5">
            <img src={AEON_LOGO_SRC} alt="ÆON" className="h-7 w-7 shrink-0 object-contain" />
            <span className="truncate text-lg font-semibold tracking-tight">ÆON Home</span>
          </Link>

          {/* Divider */}
          <span className="h-5 w-px rounded-full bg-foreground/10" />

          {/* Hamburger toggle */}
          <button
            onClick={onMenuToggle}
            aria-label="Toggle navigation"
            aria-expanded={menuOpen}
            className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition-all active:scale-95 ${
              menuOpen
                ? "bg-foreground text-background"
                : "bg-white/60 text-muted-foreground hover:bg-white hover:text-foreground"
            }`}
          >
            {menuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            <span className="font-medium">
              {menuOpen ? "Close" : "Menu"}
            </span>
          </button>

          {/* Current page breadcrumb pill */}
          {!menuOpen && (
            <span className="flex items-center gap-1.5 rounded-full bg-white/50 px-3 py-1.5 text-xs text-muted-foreground">
              <CurrentIcon className="h-3.5 w-3.5" style={{ color: "var(--aeon-purple)" }} />
              <span className="font-medium text-foreground">{currentItem?.label ?? "Dashboard"}</span>
            </span>
          )}
        </div>

        {/* Right: search + bell + avatar */}
        <div className="flex shrink-0 items-center gap-2">
          <div className="hidden xl:flex items-center gap-2 rounded-full border border-white/60 bg-white/60 px-3 py-1.5">
            <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
            <input
              placeholder="Search devices, events…"
              className="w-28 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            <kbd className="rounded bg-foreground/5 px-1.5 py-0.5 text-[10px] text-muted-foreground">⌘K</kbd>
          </div>
          <Link to="/dashboard/alerts" aria-label="Notifications" className="relative grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white/60 hover:bg-white active:scale-95 transition">
            <Bell className="h-4 w-4" />
            <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full" style={{ background: "var(--aeon-purple)", boxShadow: "0 0 8px var(--aeon-purple)" }} />
          </Link>
          <div
            className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-xs font-semibold text-background"
            style={{ background: "var(--gradient-aeon)" }}
          >
            VS
          </div>
        </div>
      </header>

      {/* ── Desktop slide-down drawer ── */}
      {menuOpen && (
        <div className="fixed inset-0 z-30 hidden lg:block">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-foreground/20 backdrop-blur-sm"
            onClick={onMenuClose}
          />

          {/* Drawer panel — slides down from top, full width, below navbar */}
          <div
            className="glass-card absolute inset-x-0 top-[57px] z-40 border-b border-white/40 p-6 shadow-2xl"
            style={{
              background: "color-mix(in oklab, white 75%, transparent)",
              backdropFilter: "blur(32px) saturate(160%)",
              animationName: "aeon-rise",
              animationDuration: "0.22s",
              animationTimingFunction: "cubic-bezier(0.22,1,0.36,1)",
              animationFillMode: "both",
            }}
          >
            {/* Section label */}
            <p className="mb-4 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              Navigation
            </p>

            {/* Nav grid — 4 columns */}
            <div className="grid grid-cols-4 gap-2 xl:grid-cols-6">
              {NAV.map((item) => {
                const Icon = item.icon;
                const isActive = item.to === current;
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    onClick={onMenuClose}
                    className={`relative flex flex-col items-center gap-2 rounded-2xl px-3 py-4 text-center text-xs font-medium transition-all active:scale-95 ${
                      isActive
                        ? "text-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                    style={
                      isActive
                        ? { background: "color-mix(in oklab, var(--aeon-purple) 10%, white)" }
                        : { background: "color-mix(in oklab, white 60%, transparent)" }
                    }
                  >
                    {/* Tinted icon badge */}
                    <span
                      className="grid h-10 w-10 place-items-center rounded-xl"
                      style={{
                        background: isActive
                          ? `color-mix(in oklab, var(--aeon-purple) 18%, white)`
                          : "color-mix(in oklab, white 80%, transparent)",
                        color: isActive ? "var(--aeon-purple)" : "oklch(0.5 0.02 275)",
                      }}
                    >
                      <Icon className="h-5 w-5" />
                    </span>
                    <span className="leading-tight">{item.label}</span>

                    {/* Active underline dot */}
                    {isActive && (
                      <span
                        className="absolute bottom-2 h-1 w-4 rounded-full"
                        style={{ background: "var(--aeon-purple)", boxShadow: "0 0 8px var(--aeon-purple)" }}
                      />
                    )}
                  </Link>
                );
              })}

              {/* Back to site tile */}
              <Link
                to="/"
                onClick={onMenuClose}
                className="flex flex-col items-center gap-2 rounded-2xl px-3 py-4 text-center text-xs font-medium text-muted-foreground transition-all hover:text-foreground active:scale-95"
                style={{ background: "color-mix(in oklab, white 60%, transparent)" }}
              >
                <span className="grid h-10 w-10 place-items-center rounded-xl" style={{ background: "color-mix(in oklab, white 80%, transparent)" }}>
                  <ArrowLeft className="h-5 w-5" />
                </span>
                <span className="leading-tight">Back to site</span>
              </Link>
            </div>

            {/* Bottom gradient fade */}
            <div
              className="pointer-events-none absolute inset-x-0 bottom-0 h-px opacity-30"
              style={{ background: "var(--gradient-aeon)" }}
            />
          </div>
        </div>
      )}
    </>
  );
}

function StatusPill({
  icon: Icon,
  label,
  value,
  tint,
}: {
  icon: typeof Wifi;
  label: string;
  value: string;
  tint: string;
}) {
  return (
    <div className="hidden items-center gap-2 rounded-full bg-white/60 px-3 py-1.5 text-xs md:flex">
      <span className="grid h-5 w-5 place-items-center rounded-full" style={{ background: `color-mix(in oklab, ${tint} 20%, white)` }}>
        <Icon className="h-3 w-3" style={{ color: tint }} />
      </span>
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
