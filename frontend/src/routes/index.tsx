import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Zap,
  ShieldCheck,
  Network,
  Sparkles,
  Cpu,
  HardDrive,
  Smartphone,
  Cloud,
  Radio,
  ArrowRight,
  Play,
  Thermometer,
  Activity,
  Timer,
  Lock,
  Database,
  BrainCircuit,
  Moon,
  LineChart,
  Circle,
} from "lucide-react";
import type { ComponentType, SVGProps } from "react";
import { Reveal } from "@/components/Reveal";
import { useEffect, useState } from "react";
import { useInView } from "@/hooks/use-in-view";
import { AEON_LOGO_SRC } from "@/lib/brand";


export const Route = createFileRoute("/")({
  component: Index,
});

function Index() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-background text-foreground">
      <AmbientGlow />
      <Navbar />
      <Hero />
      <Problem />
      <Solution />
      <Architecture />
      <Dashboard />
      <Team />
      <FinalCTA />
      <Footer />
    </div>
  );
}

/* ---------- Ambient background ---------- */
function AmbientGlow() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div
        className="absolute inset-0 opacity-70"
        style={{ background: "var(--gradient-soft)" }}
      />
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

/* ---------- Navbar ---------- */
function Navbar() {
  const links = ["Architecture", "Features", "Demo", "Team", "Contact"];
  return (
    <header className="sticky top-3 z-50 mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-3 sm:top-4 sm:px-4">
      <nav className="glass-card mx-auto flex w-full items-center justify-between rounded-full px-2 py-1.5 pl-4 sm:px-3 sm:py-2 sm:pl-5">
        <a href="#" className="flex items-center gap-2">
          <AeonMark className="h-6 w-6" />
          <span className="text-base font-semibold tracking-tight sm:text-lg">ÆON</span>
        </a>
        <ul className="hidden items-center gap-1 md:flex">
          {links.map((l) => (
            <li key={l}>
              <a
                href={`#${l.toLowerCase()}`}
                className="rounded-full px-3.5 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-white/60 hover:text-foreground"
              >
                {l}
              </a>
            </li>
          ))}
        </ul>
        <Link
          to="/dashboard/v2"
          className="group inline-flex items-center gap-1.5 rounded-full bg-foreground px-3 py-1.5 text-xs font-medium text-background transition-transform hover:scale-[1.02] sm:px-4 sm:py-2 sm:text-sm"
        >
          <span className="sm:hidden">Dashboard</span>
          <span className="hidden sm:inline">Open Dashboard</span>
          <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
        </Link>
      </nav>
    </header>

  );
}

function AeonMark({ className }: { className?: string }) {
  return (
    <img
      src={AEON_LOGO_SRC}
      alt="ÆON logo"
      className={`object-contain ${className ?? ""}`}
    />
  );
}

/* ---------- Hero ---------- */
function Hero() {
  return (
    <section className="relative mx-auto max-w-6xl px-4 pb-16 pt-12 text-center sm:pb-20 sm:pt-16 md:pb-24 md:pt-24">
      <div className="animate-rise">
        <span className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-white/60 px-3 py-1 text-xs font-medium text-muted-foreground backdrop-blur">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          Persistent intelligence · v1.0
        </span>
      </div>

      <h1
        className="mx-auto mt-5 max-w-4xl text-balance text-[2.4rem] font-semibold leading-[1.05] tracking-tight sm:text-5xl md:mt-6 md:text-7xl animate-rise"
        style={{ animationDelay: "80ms" }}
      >
        Smart devices forget.
        <br />
        <span className="text-gradient" style={{ fontFamily: "'Instrument Serif', serif", fontWeight: 400 }}>
          ÆON remembers.
        </span>
      </h1>

      <p
        className="mx-auto mt-5 max-w-2xl text-pretty text-base text-muted-foreground sm:mt-6 sm:text-lg animate-rise"
        style={{ animationDelay: "160ms" }}
      >
        A persistent intelligence fabric that survives power cuts, protects
        privacy, and evolves across every device in your home.
      </p>

      <div
        className="mt-7 flex flex-col items-stretch justify-center gap-3 px-2 sm:mt-8 sm:flex-row sm:items-center sm:px-0 animate-rise"
        style={{ animationDelay: "240ms" }}
      >
        <Link
          to="/dashboard/v2"
          className="inline-flex items-center justify-center gap-2 rounded-full bg-foreground px-5 py-3 text-sm font-medium text-background transition-transform hover:scale-[1.02]"
        >
          Open Dashboard <ArrowRight className="h-4 w-4" />
        </Link>
        <a
          href="#demo"
          className="glass-card inline-flex items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-medium text-foreground"
        >
          <Play className="h-4 w-4" /> Watch Demo
        </a>
      </div>


      {/* Dashboard preview */}
      <div className="relative mx-auto mt-20 max-w-5xl">
        <div
          className="absolute inset-x-8 -top-8 bottom-0 rounded-[40px] opacity-60 blur-3xl"
          style={{ background: "var(--gradient-aeon)" }}
        />
        <div className="glass-card relative overflow-hidden rounded-[28px] p-4 md:p-6">
          <DashboardPreview />
        </div>
      </div>
    </section>
  );
}

function DashboardPreview() {
  return (
    <div className="grid gap-4 md:grid-cols-[220px_1fr]">
      {/* Sidebar */}
      <aside className="hidden rounded-2xl bg-white/60 p-3 md:block">
        <div className="flex items-center gap-2 px-2 py-1.5">
          <AeonMark className="h-5 w-5" />
          <span className="text-sm font-semibold">ÆON Home</span>
        </div>
        <div className="mt-3 space-y-0.5">
          {[
            ["Overview", true],
            ["Devices", false],
            ["Memory", false],
            ["Privacy", false],
            ["Automations", false],
            ["Dream State", false],
          ].map(([label, active]) => (
            <div
              key={label as string}
              className={`flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm ${
                active ? "bg-foreground/5 font-medium" : "text-muted-foreground"
              }`}
            >
              <Circle className="h-1.5 w-1.5 fill-current" />
              {label}
            </div>
          ))}
        </div>
      </aside>

      {/* Main */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 text-left">
          <div>
            <p className="text-xs text-muted-foreground">Good evening, Vedaang</p>
            <h3 className="text-xl font-semibold tracking-tight">Home intelligence · Live</h3>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-700">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Persistent memory intact
          </span>
        </div>

        <div className="grid grid-cols-3 gap-2 sm:gap-3">
          <StatCard label="Recovery" fullLabel="Recovery latency" value="128" unit="ms" tint="var(--aeon-purple)" />
          <StatCard label="EEPROM" fullLabel="EEPROM usage" value="42" unit="%" tint="var(--aeon-blue)" />
          <StatCard label="Learning" fullLabel="Learning progress" value="87" unit="%" tint="var(--aeon-pink)" />
        </div>

        <div className="rounded-2xl bg-white/70 p-4 text-left">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-medium">Ambient memory trace · last 24h</p>
            <span className="text-xs text-muted-foreground">Local · encrypted</span>
          </div>
          <TraceGraph />
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  fullLabel,
  value,
  unit,
  tint,
}: {
  label: string;
  fullLabel?: string;
  value: string;
  unit: string;
  tint: string;
}) {
  const numeric = Number(value);
  return (
    <div className="relative overflow-hidden rounded-2xl bg-white/70 p-3 text-left sm:p-4">
      <div
        className="absolute -right-6 -top-6 h-20 w-20 rounded-full opacity-40 blur-2xl"
        style={{ background: tint }}
      />
      <p className="truncate text-[11px] text-muted-foreground sm:text-xs">
        <span className="sm:hidden">{label}</span>
        <span className="hidden sm:inline">{fullLabel ?? label}</span>
      </p>
      <p className="mt-1.5 text-xl font-semibold tracking-tight tabular-nums sm:mt-2 sm:text-3xl">
        {Number.isFinite(numeric) ? <CountUp to={numeric} /> : value}
        <span className="ml-1 text-xs font-normal text-muted-foreground sm:text-sm">{unit}</span>
      </p>
    </div>
  );
}

function CountUp({
  to,
  duration = 1400,
  delay = 0,
}: {
  to: number;
  duration?: number;
  delay?: number;
}) {
  const { ref, inView } = useInView<HTMLSpanElement>();
  const [value, setValue] = useState(0);
  const decimals = (to.toString().split(".")[1] ?? "").length;

  useEffect(() => {
    if (!inView) return;
    if (typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      setValue(to);
      return;
    }
    let raf = 0;
    let start = 0;
    const startTimer = window.setTimeout(() => {
      const tick = (t: number) => {
        if (!start) start = t;
        const p = Math.min(1, (t - start) / duration);
        const eased = 1 - Math.pow(1 - p, 3);
        setValue(to * eased);
        if (p < 1) raf = requestAnimationFrame(tick);
      };
      raf = requestAnimationFrame(tick);
    }, delay);
    return () => {
      window.clearTimeout(startTimer);
      cancelAnimationFrame(raf);
    };
  }, [inView, to, duration, delay]);

  return <span ref={ref}>{value.toFixed(decimals)}</span>;
}


function TraceGraph() {
  return (
    <svg viewBox="0 0 600 120" className="h-24 w-full">
      <defs>
        <linearGradient id="trace" x1="0" x2="1">
          <stop offset="0" stopColor="oklch(0.7 0.2 300)" />
          <stop offset="0.5" stopColor="oklch(0.72 0.18 250)" />
          <stop offset="1" stopColor="oklch(0.78 0.18 350)" />
        </linearGradient>
        <linearGradient id="traceFill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="oklch(0.72 0.18 280 / 0.25)" />
          <stop offset="1" stopColor="oklch(0.72 0.18 280 / 0)" />
        </linearGradient>
      </defs>
      <path
        d="M0,80 C60,60 90,40 150,50 C210,60 240,20 300,30 C360,40 390,80 450,70 C510,60 540,30 600,40 L600,120 L0,120 Z"
        fill="url(#traceFill)"
        className="trace-fill"
      />
      <path
        d="M0,80 C60,60 90,40 150,50 C210,60 240,20 300,30 C360,40 390,80 450,70 C510,60 540,30 600,40"
        stroke="url(#trace)"
        strokeWidth="2.5"
        strokeLinecap="round"
        fill="none"
        className="trace-line"
      />
      <circle r="4" fill="oklch(0.78 0.18 320)" className="trace-dot" />

    </svg>
  );
}

/* ---------- Problem ---------- */
function Problem() {
  const items = [
    { icon: Zap, label: "Amnesia after power loss" },
    { icon: Lock, label: "Cloud privacy risks" },
    { icon: Network, label: "Fragmented identity" },
    { icon: Cpu, label: "Static AI systems" },
  ];
  return (
    <section className="mx-auto max-w-6xl px-4 py-12 sm:py-16 md:py-24" id="features">
      <div className="grid gap-8 md:grid-cols-2 md:items-center md:gap-10">
        <Reveal>
          <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
            The gap
          </p>
          <h2 className="mt-3 text-3xl font-semibold leading-[1.15] tracking-tight sm:text-4xl md:text-5xl">
            The four failures of modern smart devices
          </h2>
        </Reveal>
        <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:gap-2.5">
          {items.map(({ icon: Icon, label }, i) => (
            <Reveal key={label} delay={i * 80} className="w-full sm:w-auto">
              <span className="glass-card flex h-full items-center gap-2 rounded-2xl px-3 py-2.5 text-xs font-medium sm:inline-flex sm:rounded-full sm:px-4 sm:text-sm">
                <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="min-w-0">{label}</span>
              </span>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------- Solution ---------- */
function Solution() {
  return (
    <section className="mx-auto max-w-6xl px-4 pb-12 sm:pb-16 md:pb-24" id="solution">
      <div className="glass-card rounded-[28px] p-4 sm:rounded-[32px] sm:p-6 md:p-12">
        {/* Header */}
        <Reveal as="div" className="flex flex-col items-center text-center">
          <span className="glass-card inline-flex items-center rounded-full px-3 py-1 text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground sm:px-4 sm:py-1.5 sm:text-[11px]">
            The Solution
          </span>
          <h2 className="mt-4 max-w-3xl text-3xl font-semibold leading-[1.1] tracking-tight sm:mt-6 sm:text-4xl md:text-6xl">
            The future of Natural Intelligence
          </h2>
        </Reveal>

        {/* Bento grid */}
        <div className="relative mt-6 sm:mt-10 md:mt-12">
          {/* Center logo badge */}
          <div className="pointer-events-none absolute left-1/2 top-1/2 z-20 hidden -translate-x-1/2 -translate-y-1/2 md:block">
            <Reveal variant="scale-in" delay={400}>
              <div className="relative grid h-16 w-16 place-items-center rounded-full bg-white text-foreground shadow-[0_20px_60px_-15px_rgba(0,0,0,0.2)] ring-2 ring-foreground/15">
                <span className="orbit-ring" aria-hidden />
                <img
                  src={AEON_LOGO_SRC}
                  alt="ÆON Home"
                  className="h-8 w-8 object-contain"
                />
              </div>
            </Reveal>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-5 md:auto-rows-fr">
            {/* Row 1 */}
            <Reveal className="md:col-span-3">
              <SolutionCard
                eyebrowIcon={Zap}
                title="Persistent Pulse"
                copy="State survives power cuts. EEPROM checkpoints resume home context in under 200 milliseconds — no reboots, no forgotten routines."
                tint="var(--aeon-purple)"
                visual={<PulseVisual />}
              />
            </Reveal>
            <Reveal className="md:col-span-2" delay={100}>
              <SolutionCard
                eyebrowIcon={Network}
                title="Capability Mesh"
                copy="Devices negotiate roles. Sensors, PCs and phones share compute like one organism."
                tint="var(--aeon-blue)"
                visual={<MeshVisual />}
              />
            </Reveal>

            {/* Row 2 */}
            <Reveal className="md:col-span-2" delay={200}>
              <SolutionCard
                eyebrowIcon={Sparkles}
                title="Migratory Self"
                copy="Your identity travels. Move rooms, upgrade hardware — preferences follow you."
                tint="var(--aeon-pink)"
                visual={<MigrateVisual />}
              />
            </Reveal>
            <Reveal className="md:col-span-3" delay={300}>
              <SolutionCard
                eyebrowIcon={BrainCircuit}
                title="Dream State Learning"
                copy="Idle devices consolidate memory overnight. The home learns while you sleep, refining routines and pruning noise from the day."
                tint="var(--aeon-purple)"
                visual={<DreamVisual />}
              />
            </Reveal>
          </div>
        </div>
      </div>
    </section>
  );
}

function SolutionCard({
  eyebrowIcon: Icon,
  title,
  copy,
  tint,
  visual,
  className = "",
}: {
  eyebrowIcon: ComponentType<SVGProps<SVGSVGElement>>;
  title: string;
  copy: string;
  tint: string;
  visual?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`group card-lift relative flex flex-col overflow-hidden rounded-3xl border border-white/70 bg-white/80 p-4 sm:p-6 ${className}`}
    >
      <div
        className="absolute -right-16 -top-16 h-52 w-52 rounded-full opacity-40 blur-3xl transition-opacity group-hover:opacity-70"
        style={{ background: tint }}
      />
      <div className="relative flex items-center gap-2 text-muted-foreground">
        <Icon className="h-4 w-4" />
        <h3 className="text-[15px] font-semibold tracking-tight text-foreground">
          {title}
        </h3>
      </div>
      <p className="relative mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
        {copy}
      </p>
      {visual && (
        <div className="relative mt-5 flex-1 overflow-hidden rounded-2xl">
          {visual}
        </div>
      )}
    </div>
  );
}

/* Bento visuals */
function PulseVisual() {
  return (
    <div className="relative h-full min-h-[140px] rounded-2xl bg-gradient-to-br from-white to-[oklch(0.97_0.02_280)] p-4">
      <div className="flex items-center justify-between text-[11px] text-muted-foreground">
        <span className="font-medium text-foreground">Home context</span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
          Restored 182ms
        </span>
      </div>
      <div className="mt-3">
        <TraceGraph />
      </div>
      <div className="mt-2 grid grid-cols-3 gap-2 text-[10px]">
        {["Lights", "Climate", "Presence"].map((l) => (
          <div key={l} className="rounded-lg bg-white/80 px-2 py-1.5 text-muted-foreground ring-1 ring-black/5">
            {l} <span className="ml-1 font-semibold text-foreground">OK</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MeshVisual() {
  const nodes = [
    { x: 50, y: 20, Icon: Radio },
    { x: 15, y: 60, Icon: Cpu },
    { x: 85, y: 60, Icon: Smartphone },
    { x: 50, y: 85, Icon: HardDrive },
  ];
  return (
    <div className="relative h-full min-h-[140px] rounded-2xl bg-gradient-to-br from-white to-[oklch(0.97_0.02_250)]">
      <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full" preserveAspectRatio="none">
        {nodes.map((n, i) =>
          nodes.slice(i + 1).map((m, j) => (
            <line
              key={`${i}-${j}`}
              x1={n.x} y1={n.y} x2={m.x} y2={m.y}
              stroke="oklch(0.72 0.15 260)" strokeOpacity="0.35" strokeWidth="0.4" strokeDasharray="1.5 1.5"
            />
          )),
        )}
      </svg>
      {nodes.map(({ x, y, Icon }, i) => (
        <div
          key={i}
          className="absolute grid h-8 w-8 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-xl bg-white text-foreground shadow-md ring-1 ring-black/5"
          style={{ left: `${x}%`, top: `${y}%` }}
        >
          <Icon className="h-4 w-4" />
        </div>
      ))}
    </div>
  );
}

function MigrateVisual() {
  return (
    <div className="relative h-full min-h-[140px] rounded-2xl bg-gradient-to-br from-white to-[oklch(0.97_0.03_350)] p-4">
      <div className="flex items-center justify-between">
        <div className="flex -space-x-2">
          {["A", "V", "K"].map((c, i) => (
            <div
              key={c}
              className="grid h-8 w-8 place-items-center rounded-full text-[11px] font-semibold text-white ring-2 ring-white"
              style={{ background: ["var(--aeon-purple)", "var(--aeon-blue)", "var(--aeon-pink)"][i] }}
            >
              {c}
            </div>
          ))}
        </div>
        <span className="text-[10px] text-muted-foreground">Identity sync</span>
      </div>
      <div className="mt-4 space-y-1.5">
        {["Living room → Studio", "Phone → AI PC", "Guest → Owner"].map((l) => (
          <div key={l} className="flex items-center justify-between rounded-lg bg-white/80 px-2.5 py-1.5 text-[11px] ring-1 ring-black/5">
            <span className="text-foreground">{l}</span>
            <ArrowRight className="h-3 w-3 text-muted-foreground" />
          </div>
        ))}
      </div>
    </div>
  );
}

function DreamVisual() {
  return (
    <div className="relative h-full min-h-[140px] overflow-hidden rounded-2xl bg-gradient-to-br from-[oklch(0.15_0.02_280)] to-[oklch(0.2_0.05_260)] p-4 text-white">
      <div className="flex items-center gap-2 text-[11px] text-white/70">
        <Moon className="h-3.5 w-3.5" /> Consolidating · 03:14
      </div>
      <div className="mt-4 grid grid-cols-6 items-end gap-1.5">
        {[30, 55, 40, 70, 45, 80, 60, 90, 65, 75, 50, 85].map((h, i) => (
          <div
            key={i}
            className="rounded-sm"
            style={{
              height: `${h}%`,
              minHeight: 8,
              background: `linear-gradient(180deg, var(--aeon-pink), var(--aeon-purple))`,
              opacity: 0.35 + (h / 200),
            }}
          />
        ))}
      </div>
      <div className="mt-3 flex items-center justify-between text-[10px] text-white/60">
        <span>Memory pruned 12%</span>
        <span>Routines refined 4</span>
      </div>
    </div>
  );
}

/* ---------- Architecture ---------- */
function Architecture() {
  const nodes = [
    { icon: Radio, label: "Sensors" },
    { icon: Cpu, label: "Arduino" },
    { icon: HardDrive, label: "EEPROM" },
    { icon: BrainCircuit, label: "Snapdragon AI PC" },
    { icon: Smartphone, label: "Mobile Dashboard" },
    { icon: Cloud, label: "Cloud Optimization" },
  ];
  return (
    <section className="mx-auto max-w-6xl px-4 py-16 md:py-24" id="architecture">
      <Reveal as="div" className="mx-auto max-w-2xl text-center">
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
          Architecture
        </p>
        <h2 className="mt-3 text-3xl font-semibold leading-[1.15] tracking-tight sm:text-4xl md:text-5xl">
          One fabric. From sensor to cloud.
        </h2>
        <p className="mt-4 text-muted-foreground">
          Every layer holds memory. Intelligence flows in both directions.
        </p>
      </Reveal>

      <div className="relative mt-14">
        {/* Flow */}
        <div className="grid grid-cols-2 gap-4 md:grid-cols-6">
          {nodes.map(({ icon: Icon, label }, i) => (
            <Reveal key={label} delay={i * 80} className="relative">
              <div className="glass-card flex h-full flex-col items-center gap-3 rounded-2xl p-4 text-center">
                <div
                  className="grid h-11 w-11 place-items-center rounded-xl text-white"
                  style={{ background: "var(--gradient-aeon)" }}
                >
                  <Icon className="h-5 w-5" />
                </div>
                <span className="text-sm font-medium">{label}</span>
                <span className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                  Layer {i + 1}
                </span>
              </div>
              {i < nodes.length - 1 && (
                <div className="pointer-events-none absolute right-[-10px] top-1/2 hidden -translate-y-1/2 md:block">
                  <svg width="20" height="10" viewBox="0 0 20 10">
                    <line
                      x1="0"
                      y1="5"
                      x2="20"
                      y2="5"
                      stroke="oklch(0.7 0.12 290)"
                      strokeWidth="1.5"
                      strokeDasharray="4 4"
                      style={{ animation: "aeon-pulse-line 1.2s linear infinite" }}
                    />
                  </svg>
                </div>
              )}
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------- Dashboard showcase ---------- */
function Dashboard() {
  return (
    <section className="mx-auto max-w-6xl px-4 pb-16 md:pb-24" id="demo">
      <Reveal as="div" className="mx-auto max-w-2xl text-center">
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
          Dashboard
        </p>
        <h2 className="mt-3 text-3xl font-semibold leading-[1.15] tracking-tight sm:text-4xl md:text-5xl">
          Eight windows into a living home
        </h2>
      </Reveal>

      <div className="mt-12 grid gap-4 md:grid-cols-3">
        {[
          <WidgetTemperature key="t" />,
          <WidgetMotion key="m" />,
          <WidgetRecovery key="r" />,
          <WidgetPrivacy key="p" />,
          <WidgetEEPROM key="e" />,
          <WidgetLearning key="l" />,
          <WidgetNight key="n" />,
          <WidgetDream key="d" />,
          <WidgetSummary key="s" />,
        ].map((w, i) => (
          <Reveal key={i} delay={(i % 3) * 80}>{w}</Reveal>
        ))}
      </div>
    </section>
  );
}

function WidgetShell({
  title,
  icon: Icon,
  children,
  tint,
}: {
  title: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  children: React.ReactNode;
  tint?: string;
}) {
  return (
    <div className="glass-card relative overflow-hidden rounded-3xl p-5">
      {tint && (
        <div
          className="absolute -right-8 -top-8 h-32 w-32 rounded-full opacity-30 blur-2xl"
          style={{ background: tint }}
        />
      )}
      <div className="relative flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {title}
      </div>
      <div className="relative mt-3">{children}</div>
    </div>
  );
}

function WidgetTemperature() {
  return (
    <WidgetShell title="Temperature" icon={Thermometer} tint="var(--aeon-pink)">
      <p className="text-4xl font-semibold tracking-tight">
        21.6<span className="text-lg text-muted-foreground">°C</span>
      </p>
      <p className="mt-1 text-xs text-muted-foreground">Living room · optimal</p>
      <div className="mt-3 flex h-1.5 gap-0.5">
        {Array.from({ length: 24 }).map((_, i) => (
          <div
            key={i}
            className="flex-1 rounded-full"
            style={{
              background: `oklch(${0.7 + Math.sin(i / 3) * 0.1} 0.15 ${300 + i * 2})`,
              opacity: 0.5 + (i / 30),
            }}
          />
        ))}
      </div>
    </WidgetShell>
  );
}

function WidgetMotion() {
  return (
    <WidgetShell title="Motion detection" icon={Activity} tint="var(--aeon-blue)">
      <p className="text-4xl font-semibold tracking-tight">14</p>
      <p className="mt-1 text-xs text-muted-foreground">Events · last hour</p>
      <div className="mt-3 grid grid-cols-12 gap-1">
        {Array.from({ length: 24 }).map((_, i) => (
          <div
            key={i}
            className="h-6 rounded"
            style={{
              background:
                Math.random() > 0.6
                  ? "oklch(0.72 0.18 250 / 0.7)"
                  : "oklch(0.92 0.01 280)",
            }}
          />
        ))}
      </div>
    </WidgetShell>
  );
}

function WidgetRecovery() {
  return (
    <WidgetShell title="Recovery latency" icon={Timer} tint="var(--aeon-purple)">
      <p className="text-4xl font-semibold tracking-tight">
        128<span className="text-lg text-muted-foreground">ms</span>
      </p>
      <p className="mt-1 text-xs text-muted-foreground">After last power event</p>
      <div className="mt-3 h-1.5 rounded-full bg-muted">
        <div
          className="h-full rounded-full"
          style={{ width: "24%", background: "var(--gradient-aeon)" }}
        />
      </div>
    </WidgetShell>
  );
}

function WidgetPrivacy() {
  return (
    <WidgetShell title="Privacy audit" icon={Lock}>
      <div className="flex items-baseline gap-2">
        <p className="text-4xl font-semibold tracking-tight">100%</p>
        <span className="text-xs font-medium text-emerald-700">on-device</span>
      </div>
      <ul className="mt-3 space-y-1.5 text-xs text-muted-foreground">
        <li className="flex items-center gap-2">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" /> 0 cloud writes today
        </li>
        <li className="flex items-center gap-2">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" /> All models sealed
        </li>
      </ul>
    </WidgetShell>
  );
}

function WidgetEEPROM() {
  return (
    <WidgetShell title="EEPROM usage" icon={Database} tint="var(--aeon-blue)">
      <p className="text-4xl font-semibold tracking-tight">
        42<span className="text-lg text-muted-foreground">%</span>
      </p>
      <p className="mt-1 text-xs text-muted-foreground">Persistent memory blocks</p>
      <div className="mt-3 grid grid-cols-16 gap-0.5" style={{ gridTemplateColumns: "repeat(16,1fr)" }}>
        {Array.from({ length: 32 }).map((_, i) => (
          <div
            key={i}
            className="h-2 rounded-sm"
            style={{
              background: i < 13 ? "var(--aeon-blue)" : "oklch(0.92 0.01 280)",
              opacity: i < 13 ? 0.85 : 1,
            }}
          />
        ))}
      </div>
    </WidgetShell>
  );
}

function WidgetLearning() {
  return (
    <WidgetShell title="Learning progress" icon={LineChart} tint="var(--aeon-purple)">
      <p className="text-4xl font-semibold tracking-tight">
        87<span className="text-lg text-muted-foreground">%</span>
      </p>
      <p className="mt-1 text-xs text-muted-foreground">Model convergence</p>
      <svg viewBox="0 0 200 40" className="mt-3 h-10 w-full">
        <path
          d="M0,30 C40,25 60,10 100,15 C140,20 160,5 200,8"
          stroke="var(--aeon-purple)"
          strokeWidth="2"
          fill="none"
        />
      </svg>
    </WidgetShell>
  );
}

function WidgetNight() {
  return (
    <WidgetShell title="Night mode" icon={Moon}>
      <p className="text-4xl font-semibold tracking-tight">Auto</p>
      <p className="mt-1 text-xs text-muted-foreground">Engages at 22:40</p>
      <div className="mt-3 flex items-center justify-between rounded-xl bg-foreground/5 px-3 py-2">
        <span className="text-xs">Ambient dimming</span>
        <div className="relative h-4 w-8 rounded-full bg-foreground/80">
          <div className="absolute right-0.5 top-0.5 h-3 w-3 rounded-full bg-background" />
        </div>
      </div>
    </WidgetShell>
  );
}

function WidgetDream() {
  return (
    <WidgetShell title="Dream state" icon={Sparkles} tint="var(--aeon-pink)">
      <p className="text-4xl font-semibold tracking-tight">3.2h</p>
      <p className="mt-1 text-xs text-muted-foreground">Consolidated last cycle</p>
      <div className="mt-3 flex gap-1">
        {[8, 14, 10, 18, 12, 22, 16, 20, 14].map((h, i) => (
          <div
            key={i}
            className="flex-1 rounded-t-sm"
            style={{ height: h, background: "var(--gradient-aeon)", opacity: 0.7 + i / 20 }}
          />
        ))}
      </div>
    </WidgetShell>
  );
}

function WidgetSummary() {
  return (
    <WidgetShell title="Home identity" icon={Network}>
      <p className="text-sm leading-relaxed">
        <span className="font-semibold">12 devices</span> synchronised. Migratory
        profile last written{" "}
        <span className="font-semibold">4 seconds ago</span>.
      </p>
      <div className="mt-3 flex -space-x-2">
        {["oklch(0.7 0.2 300)", "oklch(0.72 0.18 250)", "oklch(0.78 0.18 350)", "oklch(0.75 0.15 200)"].map(
          (c, i) => (
            <div
              key={i}
              className="h-7 w-7 rounded-full border-2 border-white"
              style={{ background: c }}
            />
          )
        )}
        <div className="grid h-7 w-7 place-items-center rounded-full border-2 border-white bg-foreground text-[10px] font-medium text-background">
          +8
        </div>
      </div>
    </WidgetShell>
  );
}

/* ---------- Team ---------- */
function Team() {
  const team = [
    { name: "Vedaang Sharma", role: "System Architect", initials: "VS", tint: "var(--aeon-purple)" },
    { name: "Akshat", role: "Embedded & Persistence", initials: "AK", tint: "var(--aeon-blue)" },
    { name: "Deepak", role: "AI & Cloud", initials: "DP", tint: "var(--aeon-pink)" },
    { name: "Kartik Sharma", role: "Frontend & Experience", initials: "KS", tint: "var(--aeon-purple)" },
  ];
  return (
    <section className="mx-auto max-w-6xl px-4 py-16 md:py-24" id="team">
      <Reveal as="div" className="mx-auto max-w-2xl text-center">
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
          Team
        </p>
        <h2 className="mt-3 text-3xl font-semibold leading-[1.15] tracking-tight sm:text-4xl md:text-5xl">
          Built by four minds, one system.
        </h2>
      </Reveal>

      <div className="mt-10 grid grid-cols-2 gap-3 sm:mt-12 sm:gap-4 md:grid-cols-4">
        {team.map((m, i) => (
          <Reveal key={m.name} delay={i * 80}>
            <div className="glass-card card-lift group relative overflow-hidden rounded-3xl p-4 sm:p-5">
              <div
                className="mb-3 grid h-16 w-16 place-items-center rounded-2xl text-xl font-semibold text-white transition-transform duration-500 group-hover:scale-105 group-hover:rotate-[-3deg] sm:mb-4 sm:h-24 sm:w-24 sm:text-2xl"
                style={{
                  background: `linear-gradient(135deg, ${m.tint}, var(--aeon-blue))`,
                }}
              >
                {m.initials}
              </div>
              <p className="text-sm font-semibold tracking-tight sm:text-base">{m.name}</p>
              <p className="mt-0.5 text-xs text-muted-foreground sm:mt-1 sm:text-sm">{m.role}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

/* ---------- Final CTA ---------- */
function FinalCTA() {
  return (
    <section className="mx-auto max-w-6xl px-4 pb-16 md:pb-24" id="cta">
      <Reveal variant="scale-in" className="relative overflow-hidden rounded-[32px] border border-white/60 bg-white/70 p-10 text-center md:p-16">
        <div
          className="absolute inset-0 opacity-70"
          style={{ background: "var(--gradient-soft)" }}
        />
        <div className="relative">
          <h2 className="text-3xl font-semibold leading-[1.1] tracking-tight sm:text-4xl md:text-6xl">
            This is not a smart home.
          </h2>
          <p
            className="mt-3 text-3xl font-semibold leading-[1.1] tracking-tight sm:text-4xl md:text-6xl text-gradient"
            style={{ fontFamily: "'Instrument Serif', serif", fontWeight: 400 }}
          >
            This is Natural Intelligence.
          </p>
          <p className="mx-auto mt-6 max-w-lg text-muted-foreground">
            Power cuts should pause intelligence, not erase it.
          </p>
          <a
            href="#"
            className="mt-8 inline-flex items-center gap-2 rounded-full bg-foreground px-6 py-3.5 text-sm font-medium text-background transition-transform hover:scale-[1.02]"
          >
            Build the Future <ArrowRight className="h-4 w-4" />
          </a>
        </div>
      </Reveal>
    </section>
  );
}

/* ---------- Footer ---------- */
function Footer() {
  return (
    <footer className="relative mx-auto max-w-6xl px-4 pb-8" id="contact">
      <div className="flex flex-wrap items-center justify-between gap-4 border-t border-border/60 pt-6 text-sm text-muted-foreground">
        <div className="flex items-center gap-2">
          <AeonMark className="h-5 w-5" />
          <span>ÆON Home · persistent intelligence for every device</span>
        </div>
        <div className="flex gap-5">
          <a href="#" className="hover:text-foreground">Privacy</a>
          <a href="#" className="hover:text-foreground">Docs</a>
          <a href="#" className="hover:text-foreground">Contact</a>
        </div>
      </div>
      <Reveal variant="fade-up" duration={1400}>
        <div
          aria-hidden
          className="pointer-events-none mt-8 select-none text-center text-[22vw] font-bold leading-none tracking-tighter text-transparent"
          style={{
            background: "var(--gradient-aeon)",
            WebkitBackgroundClip: "text",
            backgroundClip: "text",
            opacity: 0.22,
            fontFamily: "'Instrument Serif', serif",
            fontWeight: 400,
          }}
        >
          ÆON
        </div>
      </Reveal>
    </footer>
  );
}
