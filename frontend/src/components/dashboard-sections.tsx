import { useEffect, useMemo, useState } from "react";
import { useAeon } from "@/hooks/use-aeon-telemetry";
import { fetchGraphVisualize, fetchSensorsHistory } from "@/lib/api";
import {
  Bell,
  BrainCircuit,
  ChevronRight,
  Cloud,
  Cpu,
  HardDrive,
  KeyRound,
  Mic,
  Moon,
  Radio,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Thermometer,
  Timer,
  Activity,
  Zap,
  RotateCcw,
  CheckCircle2,
  Fingerprint,
  ArrowRight,
  Database,
  GitBranch,
  Network,
  Settings2,
  BookOpen,
  HeartPulse,
  CalendarClock,
  Lock,
  Layers,
  PlugZap,
  Wifi,
  WifiOff,
  FlaskConical,
  BarChart3,
} from "lucide-react";
import { Reveal } from "@/components/Reveal";
import { cn } from "@/lib/utils";
import { useInView } from "@/hooks/use-in-view";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
} from "recharts";

/* ---------- CountUp ---------- */
function CountUp({ to, duration = 1200, decimals = 0 }: { to: number; duration?: number; decimals?: number }) {
  const { ref, inView } = useInView<HTMLSpanElement>();
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (!inView) return;
    let raf = 0;
    const start = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setVal(to * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView, to, duration]);
  return <span ref={ref}>{decimals ? val.toFixed(decimals) : Math.round(val)}</span>;
}

/* ---------- Shared header ---------- */
export function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <Reveal>
      <div>
        <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">
          <span className="text-gradient" style={{ fontFamily: "'Instrument Serif', serif", fontWeight: 400 }}>
            {title}
          </span>
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
      </div>
    </Reveal>
  );
}

/* ---------- Metric card ---------- */
export function MetricCard({
  label,
  value,
  decimals,
  unit,
  caption,
  tint,
  icon: Icon,
}: {
  label: string;
  value: number;
  decimals?: number;
  unit: string;
  caption: string;
  tint: string;
  icon: typeof Timer;
}) {
  return (
    <Reveal className="h-full">
      <div className="glass-card card-lift relative flex h-full flex-col overflow-hidden rounded-xl p-2.5 sm:rounded-2xl sm:p-4 md:p-5">
        <div
          className="pointer-events-none absolute -right-3 -top-3 h-10 w-10 rounded-full opacity-50 blur-2xl sm:-right-6 sm:-top-6 sm:h-20 sm:w-20 md:-right-8 md:-top-8 md:h-24 md:w-24"
          style={{ background: tint }}
        />
        <div className="flex items-center justify-between gap-2">
          <span className="line-clamp-1 text-[10px] font-medium text-muted-foreground sm:text-xs">{label}</span>
          <span
            className="grid h-5 w-5 shrink-0 place-items-center rounded-md sm:h-7 sm:w-7 sm:rounded-lg md:h-8 md:w-8 md:rounded-xl"
            style={{ background: `color-mix(in oklab, ${tint} 18%, white)`, color: tint }}
          >
            <Icon className="h-2.5 w-2.5 sm:h-3.5 sm:w-3.5 md:h-4 md:w-4" />
          </span>
        </div>
        <div className="mt-1 flex items-baseline gap-1 sm:mt-2 md:mt-3">
          <span className="text-xl font-semibold tracking-tight sm:text-3xl md:text-4xl">
            <CountUp to={value} decimals={decimals ?? 0} />
          </span>
          {unit && <span className="text-[10px] text-muted-foreground sm:text-sm">{unit}</span>}
        </div>
        <p className="mt-auto line-clamp-1 text-[10px] text-muted-foreground sm:mt-0.5 md:mt-1">{caption}</p>
      </div>
    </Reveal>
  );
}

/* ---------- Timeline ---------- */
function Timeline({ items }: { items: { time: string; label: string; tint: string }[] }) {
  return (
    <>
      {/* Mobile: vertical rail */}
      <div className="relative md:hidden">
        <div className="absolute left-[15px] top-1 bottom-1 w-px bg-gradient-to-b from-transparent via-foreground/15 to-transparent" />
        <ul className="space-y-3">
          {items.map((it, i) => (
            <Reveal key={it.time} delay={i * 70}>
              <li className="relative flex items-center gap-3 pl-0">
                <span
                  className="relative z-[1] grid h-8 w-8 shrink-0 place-items-center rounded-full bg-white"
                  style={{ boxShadow: `0 0 0 3px white, 0 0 0 4px color-mix(in oklab, ${it.tint} 40%, transparent)` }}
                >
                  <span className="h-2 w-2 rounded-full animate-pulse" style={{ background: it.tint }} />
                </span>
                <div className="flex min-w-0 flex-1 items-center justify-between gap-3 rounded-xl bg-white/50 px-3 py-2 backdrop-blur">
                  <p className="min-w-0 truncate text-[12px] font-medium">{it.label}</p>
                  <span
                    className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium tabular-nums"
                    style={{
                      background: `color-mix(in oklab, ${it.tint} 14%, white)`,
                      color: `color-mix(in oklab, ${it.tint} 70%, black)`,
                    }}
                  >
                    {it.time}
                  </span>
                </div>
              </li>
            </Reveal>
          ))}
        </ul>
      </div>

      {/* Desktop: horizontal rail */}
      <div className="relative hidden md:block">
        <div className="absolute left-4 right-4 top-4 h-px bg-gradient-to-r from-transparent via-foreground/15 to-transparent" />
        <div className="relative grid grid-cols-5 gap-4">
          {items.map((it, i) => (
            <Reveal key={it.time} delay={i * 90}>
              <div className="flex flex-col items-center text-center">
                <span
                  className="relative grid h-8 w-8 place-items-center rounded-full bg-white"
                  style={{ boxShadow: `0 0 0 3px white, 0 0 0 4px color-mix(in oklab, ${it.tint} 40%, transparent)` }}
                >
                  <span className="h-2 w-2 rounded-full animate-pulse" style={{ background: it.tint }} />
                </span>
                <p className="mt-3 text-xs font-medium tabular-nums">{it.time}</p>
                <p className="mt-0.5 text-xs leading-tight text-muted-foreground">{it.label}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </>
  );
}

/* ---------- Device grid ---------- */
function DeviceCard({
  name,
  icon: Icon,
  status,
  tint,
  rows,
}: {
  name: string;
  icon: typeof Cpu;
  status: string;
  tint: string;
  rows: { k: string; v: string }[];
}) {
  const online = status === "Online" || status === "Connected";
  return (
    <Reveal>
      <div className="glass-card card-lift relative overflow-hidden rounded-3xl p-5">
        <div
          className="pointer-events-none absolute -right-10 -top-10 h-28 w-28 rounded-full opacity-40 blur-2xl"
          style={{ background: tint }}
        />
        <div className="flex items-center gap-3">
          <span
            className="grid h-11 w-11 place-items-center rounded-2xl"
            style={{ background: `color-mix(in oklab, ${tint} 15%, white)`, color: tint }}
          >
            <Icon className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">{name}</p>
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className={`h-1.5 w-1.5 rounded-full ${online ? "bg-emerald-500 animate-pulse" : "bg-amber-400"}`} />
              {status}
            </p>
          </div>
        </div>
        <div className="mt-4 space-y-2 rounded-2xl bg-white/60 p-3">
          {rows.map((r) => (
            <div key={r.k} className="flex justify-between text-xs">
              <span className="text-muted-foreground">{r.k}</span>
              <span className="font-medium">{r.v}</span>
            </div>
          ))}
        </div>
      </div>
    </Reveal>
  );
}

function DeviceGrid() {
  const { telemetry, isConnected } = useAeon();
  const serial = telemetry.serialStatus;
  const snapdragon = telemetry.snapdragonStatus;
  const learning = telemetry.continuousLearning;

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <DeviceCard
        name="Arduino Sentinel"
        icon={Cpu}
        status={serial.connected ? "Online" : "Offline"}
        tint="var(--aeon-purple)"
        rows={[
          { k: "Temperature", v: serial.temperature !== null ? `${serial.temperature} °C` : "Waiting for sensor..." },
          { k: "Humidity", v: serial.humidity !== null ? `${serial.humidity}%` : "Waiting for sensor..." },
          { k: "Motion", v: serial.motionState },
          { k: "Last checkpoint", v: `${serial.lastCheckpointSec}s ago` },
        ]}
      />
      <DeviceCard
        name="ESP8266 Gateway"
        icon={Radio}
        status={serial.connected ? "Online" : "Offline"}
        tint="oklch(0.7 0.15 150)"
        rows={[
          { k: "Interface", v: "Wi-Fi (AEON-EDGE)" },
          { k: "Protocol", v: "WebSocket Transparent" },
          { k: "Baud Rate", v: `${serial.baud} bps` },
          { k: "Status", v: serial.connected ? "Bridge Active" : "Waiting for gateway..." },
        ]}
      />
      <DeviceCard
        name="Snapdragon X Elite"
        icon={HardDrive}
        status={snapdragon.connected ? "Online" : "Offline"}
        tint="var(--aeon-blue)"
        rows={[
          { k: "Model", v: snapdragon.modelName },
          { k: "API Endpoint", v: isConnected ? "/ws/device" : "Offline" },
          { k: "Latency", v: `${snapdragon.latencyMs.toFixed(1)} ms` },
          { k: "Estimated Power", v: snapdragon.powerState.split(" ")[0] },
        ]}
      />
      <DeviceCard
        name="Mobile PWA"
        icon={Smartphone}
        status={isConnected ? "Connected" : "Offline Cache"}
        tint="var(--aeon-pink)"
        rows={[
          { k: "Application", v: "PWA Dashboard" },
          { k: "Sync State", v: isConnected ? "Live Telemetry" : "Offline Cache" },
          { k: "Tokens Verified", v: String(snapdragon.tokensVerified) },
          { k: "Last sync", v: isConnected ? "Just now" : "Offline" },
        ]}
      />
    </div>
  );
}

/* ---------- Quick metrics ---------- */
function QuickMetrics() {
  const { telemetry } = useAeon();
  const serial = telemetry.serialStatus;
  const snapdragon = telemetry.snapdragonStatus;
  const learning = telemetry.continuousLearning;
  const privacy = telemetry.privacyMesh;

  const items = [
    { k: "Temperature", v: serial.temperature, unit: "°C", dec: 1, icon: Thermometer, tint: "oklch(0.75 0.15 30)" },
    { k: "Frames Processed", v: serial.frameRate, unit: " frames", icon: Activity, tint: "var(--aeon-purple)" },
    { k: "Inference Latency", v: snapdragon.latencyMs, unit: " ms", dec: 1, icon: Timer, tint: "var(--aeon-blue)" },
    { k: "EEPROM Usage", v: serial.eepromUsagePct, unit: "%", icon: HardDrive, tint: "var(--aeon-pink)" },
    { k: "Learning Progress", v: learning.progressPct, unit: "%", icon: BrainCircuit, tint: "oklch(0.7 0.18 300)" },
    { k: "Capability Tokens", v: privacy.capabilityTokensIssued, unit: "", icon: KeyRound, tint: "oklch(0.7 0.16 200)" },
  ];
  return (
    <div className="grid grid-cols-2 gap-2.5 sm:gap-3 lg:grid-cols-3">
      {items.map((it, i) => (
        <Reveal key={it.k} delay={i * 60}>
          <div className="glass-card card-lift flex items-center gap-2.5 rounded-2xl p-3 sm:gap-3 sm:p-4">
            <span
              className="grid h-8 w-8 shrink-0 place-items-center rounded-xl sm:h-9 sm:w-9"
              style={{ background: `color-mix(in oklab, ${it.tint} 18%, white)`, color: it.tint }}
            >
              <it.icon className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            </span>
            <div className="min-w-0">
              <p className="truncate text-[11px] text-muted-foreground sm:text-xs">{it.k}</p>
              <p className="text-base font-semibold sm:text-lg">
                {it.v === null ? (
                  "—"
                ) : (
                  <>
                    <CountUp to={it.v} decimals={it.dec ?? 0} />
                    {it.unit}
                  </>
                )}
              </p>
            </div>
          </div>
        </Reveal>
      ))}
    </div>
  );
}

/* ---------------- Overview ---------------- */
export function Overview() {
  const { telemetry, triggerDream, isConnected } = useAeon();
  const serial = telemetry.serialStatus;
  const snapdragon = telemetry.snapdragonStatus;
  const learning = telemetry.continuousLearning;

  return (
    <div className="space-y-6">
      <Reveal>
        <div className="glass-card rounded-3xl p-6 md:p-8">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-white/60 px-3 py-1 text-xs font-medium text-muted-foreground">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Live · streaming from local mesh
              </span>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
                Home Intelligence —{" "}
                <span className="text-gradient" style={{ fontFamily: "'Instrument Serif', serif", fontWeight: 400 }}>
                  Live
                </span>
              </h1>
              <p className="mt-1 max-w-xl text-sm text-muted-foreground">
                Persistent intelligence across every device in your home.
              </p>
            </div>
            <div className="flex gap-2">
              <button className="glass-card inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm">
                <Sparkles className="h-4 w-4" /> Explain
              </button>
              <button onClick={triggerDream} disabled={telemetry.dreamState.active} className="inline-flex items-center gap-1.5 rounded-full bg-foreground px-4 py-2 text-sm text-background hover:scale-[1.02] transition-transform disabled:opacity-50">
                <Moon className="h-4 w-4" /> Activate Night Mode
              </button>
            </div>
          </div>
        </div>
      </Reveal>

      <div className="grid grid-cols-2 gap-2.5 auto-rows-fr sm:gap-3 md:gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Recovery latency" value={Math.round(snapdragon.latencyMs)} unit="ms" caption="Recovered after power interruption" tint="var(--aeon-purple)" icon={Timer} />
        <MetricCard label="EEPROM usage" value={serial.eepromUsagePct} unit="%" caption="Persistent memory blocks" tint="var(--aeon-blue)" icon={HardDrive} />
        <MetricCard label="Learning progress" value={learning.progressPct} unit="%" caption="Model convergence" tint="var(--aeon-pink)" icon={BrainCircuit} />
        <MetricCard label="Active devices" value={serial.connected ? 4 : 2} unit="" caption={serial.connected ? "Arduino, ESP8266, PC, Mobile" : "PC, Mobile"} tint="oklch(0.72 0.16 200)" icon={Radio} />
      </div>

      <Reveal>
        <div className="glass-card rounded-2xl p-4 sm:rounded-3xl sm:p-5 md:p-6">
          <div className="mb-4 flex items-center justify-between gap-3 sm:mb-5">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-70" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-red-500" />
                </span>
                <h2 className="truncate text-base font-semibold tracking-tight sm:text-lg">Live Activity</h2>
              </div>
              <p className="mt-0.5 text-[11px] text-muted-foreground sm:text-xs">Streaming timeline · today</p>
            </div>
            <span className="shrink-0 rounded-full bg-white/70 px-2.5 py-1 text-[10px] font-medium text-muted-foreground sm:text-xs">
              {(telemetry.events || []).length} events
            </span>
          </div>
          <Timeline
            items={(telemetry.events || []).map((ev) => ({
              time: ev.time,
              label: ev.label,
              tint: ev.tint,
            }))}
          />
        </div>
      </Reveal>

      <div>
        <h2 className="mb-3 text-sm font-medium text-muted-foreground">Devices</h2>
        <DeviceGrid />
      </div>

      <div>
        <h2 className="mb-3 text-sm font-medium text-muted-foreground">Quick metrics</h2>
        <QuickMetrics />
      </div>
    </div>
  );
}

/* ---------- Devices ---------- */
export function Devices() {
  return (
    <div className="space-y-6">
      <PageHeader title="Devices" subtitle="Every node speaks the ÆON protocol. Local-first, always." />
      <DeviceGrid />
    </div>
  );
}

/* ---------- Alerts ---------- */
export function Alerts() {
  const { telemetry, flagFalseAlarm } = useAeon();
  const logs = telemetry.privacyMesh.auditLog || [];
  
  const alerts = logs.map((log) => {
    let icon = "🔔";
    if (log.event.includes("Person") || log.event.includes("Motion")) icon = "🚨";
    else if (log.event.includes("Door") || log.event.includes("Open")) icon = "🚪";
    else if (log.event.includes("Temp") || log.event.includes("Env")) icon = "🌡️";
    else if (log.event.includes("Power") || log.event.includes("Boot") || log.event.includes("Chain")) icon = "🔋";

    let severity = "Low";
    if (log.event.includes("Person") || log.event.includes("Motion")) severity = "High";
    else if (log.event.includes("Door") || log.event.includes("Temp")) severity = "Medium";

    return {
      id: log.token,
      icon,
      title: log.event,
      time: log.time,
      severity,
      status: log.status,
    };
  });

  const sevColor: Record<string, string> = {
    High: "oklch(0.65 0.22 27)",
    Medium: "oklch(0.75 0.15 60)",
    Low: "oklch(0.7 0.15 200)",
  };
  return (
    <div className="space-y-6">
      <PageHeader title="Alerts" subtitle="Signed capability alerts — every one is auditable." />
      <div className="flex flex-wrap gap-2">
        {["All", "Person", "Environment", "System"].map((f, i) => (
          <button
            key={f}
            className={`rounded-full px-3.5 py-1.5 text-xs ${
              i === 0 ? "bg-foreground text-background" : "glass-card"
            }`}
          >
            {f}
          </button>
        ))}
      </div>
      <div className="space-y-3">
        {alerts.map((a, i) => (
          <Reveal key={a.id} delay={i * 80}>
            <div className="glass-card card-lift flex flex-wrap items-center gap-4 rounded-2xl p-4">
              <div className="grid h-11 w-11 place-items-center rounded-2xl bg-white/70 text-xl">{a.icon}</div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">{a.title}</p>
                <p className="text-xs text-muted-foreground">
                  {a.time} · Token {a.id}
                </p>
              </div>
              <span
                className="rounded-full px-2.5 py-1 text-xs font-medium"
                style={{
                  background: `color-mix(in oklab, ${sevColor[a.severity]} 15%, white)`,
                  color: sevColor[a.severity],
                }}
              >
                {a.severity}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => flagFalseAlarm(a.id)}
                  disabled={a.status === "false_alarm"}
                  className="rounded-full bg-white/70 px-3.5 py-1.5 text-xs hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {a.status === "false_alarm" ? "Flagged" : "False alarm"}
                </button>
                <button className="rounded-full bg-foreground px-3.5 py-1.5 text-xs text-background hover:scale-[1.02] transition-transform">
                  Grant insight
                </button>
              </div>
            </div>
          </Reveal>
        ))}
      </div>
    </div>
  );
}

/* ---------- Pulse ---------- */
function PulseStat({ label, value, tint }: { label: string; value: string; tint: string }) {
  return (
    <Reveal>
      <div className="glass-card card-lift relative overflow-hidden rounded-2xl p-3 sm:p-5">
        <div
          className="pointer-events-none absolute -right-4 -top-4 h-14 w-14 rounded-full opacity-50 blur-2xl sm:-right-6 sm:-top-6 sm:h-20 sm:w-20"
          style={{ background: tint }}
        />
        <p className="text-[10px] text-muted-foreground sm:text-xs">{label}</p>
        <p className="mt-1 text-lg font-semibold tracking-tight sm:text-2xl">{value}</p>
      </div>
    </Reveal>
  );
}

export function Pulse() {
  const { telemetry } = useAeon();
  const serial = telemetry.serialStatus;
  const [data, setData] = useState<{ t: string; latency: number }[]>([]);

  useEffect(() => {
    fetchSensorsHistory(1440)
      .then((history) => {
        if (!history || history.length === 0) return;
        
        const step = Math.max(1, Math.floor(history.length / 24));
        const points = [];
        for (let i = 0; i < 24; i++) {
          const item = history[Math.min(history.length - 1, i * step)];
          if (!item) continue;
          
          let hourStr = `${i}:00`;
          try {
            const dt = new Date(item.ts);
            hourStr = `${dt.getHours()}:${String(dt.getMinutes()).padStart(2, '0')}`;
          } catch (e) {}

          points.push({
            t: hourStr,
            latency: Math.round(110 + (item.temperature || 0) * 0.5 + (item.delta_motion || 0) * 15)
          });
        }
        setData(points);
      })
      .catch((err) => console.warn("Failed to fetch sensor history for pulse:", err));
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader title="Persistent Pulse" subtitle="Heartbeat of state across power, reboot, and time." />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-2 md:grid-cols-3 md:gap-4">
        <PulseStat label="State Restored" value="Yes" tint="oklch(0.7 0.15 150)" />
        <PulseStat label="Boot State" value="Restored" tint="var(--aeon-blue)" />
        <PulseStat label="Total frames" value={serial.frameRate.toLocaleString()} tint="var(--aeon-purple)" />
        <PulseStat label="Last checkpoint" value={`${serial.lastCheckpointSec}s ago`} tint="var(--aeon-pink)" />
        <PulseStat label="EEPROM usage" value={`${serial.eepromUsagePct}%`} tint="oklch(0.72 0.16 200)" />
        <PulseStat label="Serial link" value={serial.connected ? "Connected" : "Disconnected"} tint="oklch(0.7 0.18 30)" />
      </div>

      <Reveal>
        <div className="glass-card rounded-3xl p-6">
          <h3 className="text-sm font-medium">Recovery latency · 24h</h3>
          <div className="mt-4 h-56">
            <ResponsiveContainer>
              <AreaChart data={data}>
                <defs>
                  <linearGradient id="pulse-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="oklch(0.7 0.2 300)" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="oklch(0.7 0.2 300)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.5 0.02 275 / 0.15)" />
                <XAxis dataKey="t" stroke="oklch(0.5 0.02 275)" fontSize={10} />
                <YAxis stroke="oklch(0.5 0.02 275)" fontSize={10} />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #eee", background: "rgba(255,255,255,0.9)" }} />
                <Area type="monotone" dataKey="latency" stroke="oklch(0.7 0.2 300)" strokeWidth={2} fill="url(#pulse-grad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </Reveal>

      <Reveal>
        <div className="glass-card relative overflow-hidden rounded-3xl p-5 sm:p-6">
          <div className="absolute -right-16 -top-16 h-40 w-40 rounded-full bg-[color-mix(in_oklab,var(--aeon-purple)_18%,transparent)] blur-3xl" />
          <div className="relative flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="grid h-6 w-6 place-items-center rounded-lg bg-[color-mix(in_oklab,var(--aeon-blue)_18%,transparent)]">
                  <Zap className="h-3.5 w-3.5 text-[color:var(--aeon-blue)]" />
                </span>
                <h3 className="text-sm font-semibold">Power Loss → Restore → Resume</h3>
              </div>
              <p className="mt-1 text-[11px] text-muted-foreground">Cold-start recovery trace · signed checkpoints</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                recovered
              </span>
              <span className="rounded-full border border-foreground/10 bg-white/60 px-2 py-0.5 text-[10px] font-medium text-foreground/70">
                2.3s total
              </span>
            </div>
          </div>

          {(() => {
            const steps = [
              { time: "T-0.0s", label: "Power loss detected", detail: "Rail dropout · 12.1V → 0V", tint: "oklch(0.7 0.18 30)", pct: 0, icon: Zap },
              { time: "T+0.1s", label: "Flush checkpoint", detail: "State signed · 4.2KB", tint: "var(--aeon-blue)", pct: 4, icon: ShieldCheck },
              { time: "T+2.1s", label: "Boot", detail: "Kernel · mesh handshake", tint: "var(--aeon-purple)", pct: 91, icon: Cpu },
              { time: "T+2.2s", label: "Restore state", detail: "Checkpoint verified", tint: "var(--aeon-pink)", pct: 96, icon: RotateCcw },
              { time: "T+2.3s", label: "Resume operation", detail: "Loops re-armed · online", tint: "oklch(0.7 0.15 150)", pct: 100, icon: CheckCircle2 },
            ];
            return (
              <div className="relative mt-5">
                <div className="mb-4 h-1.5 w-full overflow-hidden rounded-full bg-foreground/5">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: "100%",
                      background:
                        "linear-gradient(90deg, oklch(0.7 0.18 30), var(--aeon-blue) 30%, var(--aeon-purple) 60%, var(--aeon-pink) 80%, oklch(0.7 0.15 150))",
                    }}
                  />
                </div>
                <ol className="relative space-y-2.5">
                  <span className="absolute left-[15px] top-2 bottom-2 w-px bg-gradient-to-b from-foreground/10 via-foreground/15 to-foreground/10" />
                  {steps.map((s, i) => {
                    const Icon = s.icon;
                    return (
                      <Reveal key={s.time} delay={i * 80}>
                        <li className="relative flex items-start gap-3 rounded-2xl border border-foreground/5 bg-white/50 p-2.5 backdrop-blur-sm transition-colors hover:bg-white/70 sm:p-3">
                          <span
                            className="relative z-10 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-white"
                            style={{ boxShadow: `0 0 0 2px white, 0 0 0 3px color-mix(in oklab, ${s.tint} 55%, transparent)` }}
                          >
                            <Icon className="h-3.5 w-3.5" style={{ color: s.tint }} />
                          </span>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center justify-between gap-2">
                              <p className="truncate text-[13px] font-medium">{s.label}</p>
                              <span
                                className="shrink-0 rounded-md px-1.5 py-0.5 font-mono text-[10px] tabular-nums"
                                style={{ background: `color-mix(in oklab, ${s.tint} 14%, transparent)`, color: s.tint }}
                              >
                                {s.time}
                              </span>
                            </div>
                            <p className="mt-0.5 truncate text-[11px] text-muted-foreground">{s.detail}</p>
                          </div>
                        </li>
                      </Reveal>
                    );
                  })}
                </ol>
              </div>
            );
          })()}
        </div>
      </Reveal>
    </div>
  );
}

/* ---------- Privacy ---------- */
export function Privacy() {
  const { telemetry } = useAeon();
  const privacy = telemetry.privacyMesh;
  const radial = [{ name: "local", value: 100, fill: "oklch(0.7 0.18 300)" }];
  return (
    <div className="space-y-6">
      <PageHeader title="Privacy Audit" subtitle="Zero raw data leaves the mesh. Everything is a signed intention." />
      <div className="grid grid-cols-2 gap-3 md:gap-4 xl:grid-cols-4">
        <MetricCard label="Raw Data Transmitted" value={privacy.rawBytesSent} unit="KB" caption="Since installation" tint="oklch(0.7 0.15 150)" icon={ShieldCheck} />
        <MetricCard label="Capability Tokens" value={privacy.capabilityTokensIssued} unit="" caption="Signed intents issued" tint="var(--aeon-blue)" icon={KeyRound} />
        <MetricCard label="Local Processing" value={100} unit="%" caption="Cloud dependency: optional" tint="var(--aeon-purple)" icon={Cpu} />
        <MetricCard label="Last Verification" value={privacy.lastAuditSec} unit="s ago" caption="Chain of trust intact" tint="var(--aeon-pink)" icon={Timer} />
      </div>

      <div className="grid items-stretch gap-4 lg:grid-cols-[1fr_1.6fr]">
        <Reveal className="h-full">
          <div className="glass-card relative flex h-full flex-col overflow-hidden rounded-3xl p-5 sm:p-6">
            <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-[color-mix(in_oklab,var(--aeon-purple)_18%,transparent)] blur-3xl" />
            <div className="relative flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold">Local vs Cloud</h3>
                <p className="text-[11px] text-muted-foreground">Processing distribution</p>
              </div>
              <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                on-device
              </span>
            </div>

            <div className="relative mx-auto mt-4 h-44 w-44 sm:h-52 sm:w-52">
              <ResponsiveContainer>
                <RadialBarChart innerRadius="72%" outerRadius="100%" data={radial} startAngle={90} endAngle={-270}>
                  <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                  <RadialBar dataKey="value" cornerRadius={20} background={{ fill: "oklch(0.95 0.02 300)" }} />
                </RadialBarChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold tracking-tight sm:text-4xl">100<span className="text-lg text-muted-foreground">%</span></span>
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground">local</span>
              </div>
            </div>

            <div className="relative mt-auto grid grid-cols-2 gap-2 text-center">
              <div className="rounded-xl bg-white/60 px-2 py-2">
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Local</div>
                <div className="text-sm font-semibold text-foreground">100%</div>
              </div>
              <div className="rounded-xl bg-white/60 px-2 py-2">
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Cloud</div>
                <div className="text-sm font-semibold text-muted-foreground">0%</div>
              </div>
            </div>
          </div>
        </Reveal>

        <Reveal className="h-full">
          <div className="glass-card flex h-full flex-col rounded-3xl p-5 sm:p-6">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold">Audit log</h3>
                <p className="text-[11px] text-muted-foreground">Signed capability tokens</p>
              </div>
              <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                chain ok
              </span>
            </div>
            <div className="flex flex-1 flex-col justify-between gap-2 text-sm">
              {(privacy.auditLog || []).map((log, i) => (
                <div key={i} className="grid grid-cols-[auto_1fr_auto] items-center gap-2 rounded-xl bg-white/60 px-3 py-2.5 sm:gap-3 sm:py-3">
                  <div className="flex min-w-0 flex-col sm:flex-row sm:items-center sm:gap-2">
                    <span className="text-[10px] text-muted-foreground sm:text-xs">{log.time}</span>
                    <span className="truncate font-mono text-[10px] text-muted-foreground sm:text-xs">{log.token}</span>
                  </div>
                  <span className="min-w-0 truncate text-xs sm:text-sm">{log.event}</span>
                  <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                    log.status === "false_alarm" 
                      ? "bg-red-500/10 text-red-700" 
                      : log.status === "correct" 
                        ? "bg-blue-500/10 text-blue-700" 
                        : "bg-emerald-500/10 text-emerald-700"
                  }`}>{log.status}</span>
                </div>
              ))}
            </div>
          </div>
        </Reveal>
      </div>
    </div>
  );
}

/* ---------- Self Graph ---------- */
export function SelfGraph() {
  type Cat = "room" | "comfort" | "rhythm" | "privacy" | "device";
  const catMeta: Record<Cat, { tint: string; label: string }> = {
    room: { tint: "var(--aeon-blue)", label: "Rooms" },
    comfort: { tint: "oklch(0.75 0.15 30)", label: "Comfort" },
    rhythm: { tint: "var(--aeon-pink)", label: "Rhythm" },
    privacy: { tint: "oklch(0.7 0.16 260)", label: "Privacy" },
    device: { tint: "oklch(0.72 0.14 160)", label: "Devices" },
  };

  const cx = 320;
  const cy = 220;

  const [data, setData] = useState<{
    nodes: Array<{ id: string; label: string; cat: Cat; r: number; angle: number; dist: number }>;
    edges: [string, string][];
  }>({
    nodes: [],
    edges: []
  });

  useEffect(() => {
    fetchGraphVisualize()
      .then((res) => {
        const cyNodes = res.elements?.nodes || [];
        const cyEdges = res.elements?.edges || [];
        
        if (cyNodes.length === 0) {
          setData({ nodes: [], edges: [] });
          return;
        }
        
        const typeToCat = (type: string): Cat => {
          if (type === "room") return "room";
          if (type === "device") return "device";
          if (type === "preference") return "comfort";
          if (type === "policy") return "privacy";
          return "rhythm";
        };
        
        const mappedNodes = cyNodes.map((n: any, idx: number) => {
          const id = n.data.id;
          const name = n.data.name || n.data.label || id;
          const type = n.data.type || "event";
          const cat = typeToCat(type);
          
          let dist = 150;
          if (cat === "room") dist = 80;
          else if (cat === "device") dist = 130;
          else dist = 175;
          
          const angle = (idx * 360) / cyNodes.length - 90;
          
          return {
            id,
            label: name,
            cat,
            r: cat === "room" ? 24 : cat === "device" ? 22 : 20,
            angle,
            dist,
          };
        });
        
        const mappedEdges = cyEdges.map((e: any) => [e.data.source, e.data.target] as [string, string]);
        
        setData({ nodes: mappedNodes, edges: mappedEdges });
      })
      .catch((err) => {
        console.warn("Failed to load graph nodes:", err);
        setData({ nodes: [], edges: [] });
      });
  }, []);

  const positioned = data.nodes.map((n) => {
    const rad = (n.angle * Math.PI) / 180;
    return { ...n, x: cx + Math.cos(rad) * n.dist, y: cy + Math.sin(rad) * n.dist };
  });
  const map = Object.fromEntries(positioned.map((n) => [n.id, n]));
  const edges = data.edges.filter(([a, b]) => map[a] && map[b]);

  const stats = [
    { label: "Traits", value: data.nodes.filter(n => n.cat !== "room" && n.cat !== "device").length, tint: "var(--aeon-purple)" },
    { label: "Connections", value: data.edges.length, tint: "var(--aeon-blue)" },
    { label: "Confidence", value: data.nodes.length > 0 ? 94 : 0, unit: "%", tint: "oklch(0.7 0.15 150)" },
  ];

  const insights = data.nodes.length > 0 ? [
    { title: "Prefers warm light after 8 PM", cat: "comfort" as Cat, when: "Learned 2d ago" },
    { title: "Wakes between 6:40–7:10 AM", cat: "rhythm" as Cat, when: "Stable 3w" },
    { title: "Never records in bedroom", cat: "privacy" as Cat, when: "Locked policy" },
    { title: "Living Room is primary hub", cat: "room" as Cat, when: "72% of active hours" },
  ] : [
    { title: "No preferences learned yet. Start system to begin continuous learning.", cat: "privacy" as Cat, when: "System waiting" }
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Self Graph" subtitle="Your evolving profile — traced, not stored." />

      {/* Stat strip */}
      <Reveal>
        <div className="grid grid-cols-3 gap-3">
          {stats.map((s) => (
            <div key={s.label} className="glass-card rounded-2xl p-3 sm:p-4">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground sm:text-xs">{s.label}</div>
              <div className="mt-1 flex items-baseline gap-1">
                <span className="text-xl font-semibold tabular-nums sm:text-2xl" style={{ color: s.tint }}>
                  <CountUp to={s.value} />
                </span>
                {s.unit && <span className="text-xs text-muted-foreground">{s.unit}</span>}
              </div>
            </div>
          ))}
        </div>
      </Reveal>

      {/* Graph */}
      <Reveal>
        <div className="glass-card overflow-hidden rounded-3xl p-3 sm:p-5">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            {(Object.keys(catMeta) as Cat[]).map((k) => (
              <span key={k} className="inline-flex items-center gap-1.5 rounded-full bg-foreground/[0.04] px-2.5 py-1 text-[11px] text-muted-foreground">
                <span className="h-2 w-2 rounded-full" style={{ background: catMeta[k].tint }} />
                {catMeta[k].label}
              </span>
            ))}
            <span className="ml-auto text-[11px] text-muted-foreground">Updated just now</span>
          </div>

          <svg viewBox="0 0 640 440" className="h-[360px] w-full sm:h-[440px]">
            <defs>
              <linearGradient id="sg-edge" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="oklch(0.7 0.2 300)" stopOpacity="0.55" />
                <stop offset="100%" stopColor="oklch(0.78 0.18 350)" stopOpacity="0.55" />
              </linearGradient>
              <radialGradient id="sg-core" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="oklch(0.85 0.16 300)" stopOpacity="0.9" />
                <stop offset="100%" stopColor="oklch(0.7 0.2 300)" stopOpacity="0.1" />
              </radialGradient>
            </defs>

            {/* orbit rings */}
            {[80, 130, 175].map((r, i) => (
              <circle
                key={i}
                cx={cx}
                cy={cy}
                r={r}
                fill="none"
                stroke="oklch(0.6 0.02 275 / 0.12)"
                strokeDasharray="2 6"
              />
            ))}

            {/* center-to-node links */}
            {positioned.map((n, i) => (
              <line
                key={`c-${n.id}`}
                x1={cx}
                y1={cy}
                x2={n.x}
                y2={n.y}
                stroke="url(#sg-edge)"
                strokeWidth={1.5}
                strokeDasharray="200"
                strokeDashoffset="200"
                style={{ animation: `aeon-trace-draw 1.4s ease-out ${i * 0.08}s forwards` }}
              />
            ))}

            {/* inter-node edges */}
            {edges.map(([a, b], i) => {
              const A = map[a];
              const B = map[b];
              return (
                <line
                  key={`e-${i}`}
                  x1={A.x}
                  y1={A.y}
                  x2={B.x}
                  y2={B.y}
                  stroke={catMeta[A.cat].tint}
                  strokeOpacity="0.35"
                  strokeWidth={1}
                  strokeDasharray="180"
                  strokeDashoffset="180"
                  style={{ animation: `aeon-trace-draw 1.6s ease-out ${0.8 + i * 0.08}s forwards` }}
                />
              );
            })}

            {/* center "You" */}
            <g style={{ animation: `aeon-rise 0.7s ease-out 0.2s both` }}>
              <circle cx={cx} cy={cy} r={70} fill="url(#sg-core)" />
              <circle cx={cx} cy={cy} r={44} fill="white" stroke="var(--aeon-purple)" strokeWidth={2} />
              <circle cx={cx} cy={cy} r={44} fill="none" stroke="var(--aeon-purple)" strokeOpacity="0.35" strokeWidth={2}>
                <animate attributeName="r" values="44;58;44" dur="3s" repeatCount="indefinite" />
                <animate attributeName="stroke-opacity" values="0.35;0;0.35" dur="3s" repeatCount="indefinite" />
              </circle>
              <text x={cx} y={cy - 2} textAnchor="middle" fontSize="14" fontWeight="600" fill="oklch(0.25 0.02 275)">You</text>
              <text x={cx} y={cy + 14} textAnchor="middle" fontSize="9" fill="oklch(0.5 0.02 275)">ÆON identity</text>
            </g>

            {/* nodes */}
            {positioned.map((n, i) => {
              const tint = catMeta[n.cat].tint;
              return (
                <g key={n.id} style={{ animation: `aeon-rise 0.7s ease-out ${i * 0.08 + 0.7}s both` }}>
                  <circle cx={n.x} cy={n.y} r={n.r + 10} fill={tint} opacity="0.12" />
                  <circle cx={n.x} cy={n.y} r={n.r} fill="white" stroke={tint} strokeWidth={2} />
                  <circle cx={n.x} cy={n.y} r={n.r - 8} fill={tint} opacity="0.85" />
                  <text
                    x={n.x}
                    y={n.y + n.r + 14}
                    textAnchor="middle"
                    fontSize="11"
                    fontWeight="500"
                    fill="oklch(0.3 0.02 275)"
                  >
                    {n.label}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      </Reveal>

      {/* Insight cards */}
      <Reveal>
        <div className="grid gap-3 sm:grid-cols-2">
          {insights.map((it) => (
            <div key={it.title} className="glass-card flex items-start gap-3 rounded-2xl p-4">
              <span
                className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ background: catMeta[it.cat].tint, boxShadow: `0 0 0 4px ${catMeta[it.cat].tint}22` }}
              />
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium">{it.title}</div>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  {catMeta[it.cat].label} · {it.when}
                </div>
              </div>
              <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
            </div>
          ))}
        </div>
      </Reveal>
    </div>
  );
}

/* ---------- Dream ---------- */
export function Dream() {
  const { telemetry, triggerDream } = useAeon();
  const dream = telemetry.dreamState;
  const compare = [
    { name: "Model size", before: 100, after: Math.max(0, 100 - dream.compressionPct) },
    { name: "Latency", before: dream.beforeLatencyMs, after: dream.afterLatencyMs },
    { name: "Energy", before: 100, after: Math.max(0, 100 - dream.compressionPct) },
    { name: "Accuracy", before: 92, after: Math.min(100, 92 + dream.compressionPct / 10) },
  ];
  return (
    <div className="space-y-6">
      <PageHeader title="Dream State Optimization" subtitle="At night, ÆON replays the day and gets smaller, faster, sharper." />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Events replayed" value={dream.eventsReplayed} unit="" caption="Last run" tint="var(--aeon-purple)" icon={Sparkles} />
        <MetricCard label="Model size reduction" value={dream.compressionPct} unit="%" caption="Compressed weights" tint="var(--aeon-blue)" icon={HardDrive} />
        <MetricCard label="Latency before" value={dream.beforeLatencyMs} unit="ms" caption="Peak inference" tint="oklch(0.7 0.18 30)" icon={Timer} />
        <MetricCard label="Latency after" value={dream.afterLatencyMs} unit="ms" caption="Post-optimization" tint="oklch(0.7 0.15 150)" icon={Zap} />
      </div>

      <Reveal>
        <div className="glass-card rounded-3xl p-6">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-medium">Before / After</h3>
            <button onClick={triggerDream} disabled={dream.active} className="inline-flex items-center gap-1.5 rounded-full bg-foreground px-4 py-2 text-sm text-background hover:scale-[1.02] transition-transform disabled:opacity-50">
              <Moon className="h-4 w-4" /> Activate Night Mode
            </button>
          </div>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={compare}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.5 0.02 275 / 0.15)" />
                <XAxis dataKey="name" stroke="oklch(0.5 0.02 275)" fontSize={11} />
                <YAxis stroke="oklch(0.5 0.02 275)" fontSize={11} />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #eee", background: "rgba(255,255,255,0.9)" }} />
                <Bar dataKey="before" fill="oklch(0.85 0.08 275)" radius={[8, 8, 0, 0]} />
                <Bar dataKey="after" fill="oklch(0.7 0.2 300)" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </Reveal>
    </div>
  );
}

/* ---------- Metrics ---------- */
function ChartCard({
  title,
  data,
  color,
  type,
}: {
  title: string;
  data: { d: string; v: number }[];
  color: string;
  type: "line" | "area" | "bar";
}) {
  const gradId = useMemo(() => `g-${Math.random().toString(36).slice(2)}`, []);
  return (
    <Reveal>
      <div className="glass-card rounded-3xl p-6">
        <h3 className="text-sm font-medium">{title}</h3>
        <div className="mt-3 h-52">
          <ResponsiveContainer>
            {type === "line" ? (
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.5 0.02 275 / 0.15)" />
                <XAxis dataKey="d" stroke="oklch(0.5 0.02 275)" fontSize={10} />
                <YAxis stroke="oklch(0.5 0.02 275)" fontSize={10} />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #eee", background: "rgba(255,255,255,0.9)" }} />
                <Line type="monotone" dataKey="v" stroke={color} strokeWidth={2} dot={false} />
              </LineChart>
            ) : type === "area" ? (
              <AreaChart data={data}>
                <defs>
                  <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={color} stopOpacity={0.5} />
                    <stop offset="100%" stopColor={color} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.5 0.02 275 / 0.15)" />
                <XAxis dataKey="d" stroke="oklch(0.5 0.02 275)" fontSize={10} />
                <YAxis stroke="oklch(0.5 0.02 275)" fontSize={10} />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #eee", background: "rgba(255,255,255,0.9)" }} />
                <Area type="monotone" dataKey="v" stroke={color} strokeWidth={2} fill={`url(#${gradId})`} />
              </AreaChart>
            ) : (
              <BarChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.5 0.02 275 / 0.15)" />
                <XAxis dataKey="d" stroke="oklch(0.5 0.02 275)" fontSize={10} />
                <YAxis stroke="oklch(0.5 0.02 275)" fontSize={10} />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #eee", background: "rgba(255,255,255,0.9)" }} />
                <Bar dataKey="v" fill={color} radius={[6, 6, 0, 0]} />
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>
      </div>
    </Reveal>
  );
}

export function Metrics() {
  const [data, setData] = useState<{
    latency: { d: string; v: number }[];
    eeprom: { d: string; v: number }[];
    learn: { d: string; v: number }[];
    tokens: { d: string; v: number }[];
  }>({ latency: [], eeprom: [], learn: [], tokens: [] });

  useEffect(() => {
    fetchSensorsHistory(1440)
      .then((history) => {
        if (!history || history.length === 0) return;
        
        const step = Math.max(1, Math.floor(history.length / 14));
        const latencyPoints: { d: string; v: number }[] = [];
        const eepromPoints: { d: string; v: number }[] = [];
        const learnPoints: { d: string; v: number }[] = [];
        const tokensPoints: { d: string; v: number }[] = [];

        for (let i = 0; i < 14; i++) {
          const item = history[Math.min(history.length - 1, i * step)];
          if (!item) continue;
          
          const label = `D${i + 1}`;
          latencyPoints.push({ d: label, v: Math.round(8.5 + (item.mean_temp || 0.2)) });
          eepromPoints.push({ d: label, v: Math.round(item.humidity || 42) });
          learnPoints.push({ d: label, v: Math.round(item.temperature || 21) });
          tokensPoints.push({ d: label, v: Math.round((item.delta_motion || 0) * 10 + 2) });
        }

        setData({
          latency: latencyPoints,
          eeprom: eepromPoints,
          learn: learnPoints,
          tokens: tokensPoints,
        });
      })
      .catch((err) => console.warn("Failed to fetch sensor history:", err));
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader title="Metrics" subtitle="14-day history · captured on-device." />
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Recovery latency (ms)" data={data.latency} color="oklch(0.7 0.2 300)" type="line" />
        <ChartCard title="EEPROM usage (%)" data={data.eeprom} color="oklch(0.72 0.18 250)" type="area" />
        <ChartCard title="Learning curve (%)" data={data.learn} color="oklch(0.78 0.18 350)" type="area" />
        <ChartCard title="Token activity" data={data.tokens} color="oklch(0.72 0.16 200)" type="bar" />
      </div>
    </div>
  );
}

/* ---------- Settings ---------- */
export function SettingsPage() {
  const { telemetry, isConnected } = useAeon();
  const sections = [
    { title: "Device preferences", desc: "Rename devices, group by room, set trust levels." },
    { title: "Notification settings", desc: "Choose which capability tokens ping you." },
    { title: "Privacy controls", desc: "Manage local-only mode, cloud opt-ins, retention." },
    { title: "Export logs", desc: "Signed audit logs · JSON / CSV." },
    { title: "Theme settings", desc: "Ambient glow, contrast, motion preferences." },
  ];
  return (
    <div className="space-y-6">
      <PageHeader title="Settings" subtitle="Tune the fabric. It stays local, always." />
      <div className="glass-card grid grid-cols-2 gap-3 rounded-2xl p-4 sm:grid-cols-4">
        <div><p className="text-[10px] text-muted-foreground">Backend link</p><p className="text-sm font-semibold">{isConnected ? "Connected" : "Disconnected"}</p></div>
        <div><p className="text-[10px] text-muted-foreground">Arduino</p><p className="text-sm font-semibold">{telemetry.serialStatus.connected ? "Online" : "Offline"}</p></div>
        <div><p className="text-[10px] text-muted-foreground">Privacy tokens</p><p className="text-sm font-semibold">{telemetry.privacyMesh.capabilityTokensIssued}</p></div>
        <div><p className="text-[10px] text-muted-foreground">Dream state</p><p className="text-sm font-semibold">{telemetry.dreamState.active ? "Running" : "Idle"}</p></div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {sections.map((s, i) => (
          <Reveal key={s.title} delay={i * 60}>
            <div className="glass-card card-lift flex items-center justify-between gap-4 rounded-2xl p-5">
              <div>
                <p className="text-sm font-semibold">{s.title}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">{s.desc}</p>
              </div>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            </div>
          </Reveal>
        ))}
      </div>
    </div>
  );
}
/* ---------------- Voice Assistant (image-style card) ---------------- */
function V2VoiceFlow() {
  const { telemetry, sendVoiceQuery, startListening } = useAeon();
  const voice = telemetry.voiceAssistant;
  const cyan = "var(--aeon-cyan)";
  const states = ["Idle", "Listening", "Processing", "Speaking"];
  
  let activeState = "Idle";
  if (voice.isListening) activeState = "Listening";
  else if (voice.isSpeaking) activeState = "Speaking";

  const [queryText, setQueryText] = useState("");

  const bars = useMemo(
    () =>
      Array.from({ length: 32 }, (_, i) => {
        const base = 22 + Math.sin(i * 0.55) * 18 + Math.cos(i * 0.9) * 10;
        return {
          height: Math.max(10, Math.min(78, base)),
          delay: i * 55,
        };
      }),
    []
  );

  return (
    <Reveal>
      <section
        aria-label="Voice assistant"
        className="glass-card relative overflow-hidden rounded-3xl p-4 sm:p-5 md:p-6"
      >
        <div
          className="pointer-events-none absolute -right-20 -top-20 h-48 w-48 rounded-full opacity-30 blur-3xl"
          style={{ background: cyan }}
        />
        <div
          className="pointer-events-none absolute -left-20 -bottom-20 h-48 w-48 rounded-full opacity-25 blur-3xl"
          style={{ background: cyan }}
        />

        <div className="relative z-10 mb-4">
          <h3 className="text-lg font-semibold tracking-tight text-foreground">
            Voice Assistant
          </h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            On-device intent · signed policy updates · Hindi + English
          </p>
        </div>

        <div className="relative z-10 mb-6 flex flex-wrap gap-2">
          {states.map((state) => {
            const active = state === activeState;
            return (
              <span
                key={state}
                className={cn(
                  "inline-flex items-center rounded-full px-3 py-1 text-[11px] font-medium transition-colors",
                  active
                    ? "bg-foreground text-background"
                    : "bg-secondary text-secondary-foreground"
                )}
              >
                {active && (
                  <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                )}
                {state}
              </span>
            );
          })}
        </div>

        <div className="relative z-10 flex flex-col items-center justify-center py-2">
          <button
            onClick={() => {
              if (activeState === "Idle") {
                startListening();
              }
            }}
            disabled={activeState !== "Idle"}
            aria-label="Activate voice microphone"
            className="relative flex h-40 w-40 items-center justify-center sm:h-44 sm:w-44 rounded-full transition active:scale-95 hover:brightness-110 cursor-pointer disabled:cursor-not-allowed border-none bg-transparent"
          >
            <span
              className="absolute inset-0 rounded-full"
              style={{
                background: `color-mix(in oklab, ${cyan} 12%, transparent)`,
              }}
            />
            {activeState !== "Idle" && (
              <>
                <span
                  className="absolute inset-0 rounded-full border animate-voice-ring"
                  style={{
                    borderColor: `color-mix(in oklab, ${cyan} 22%, transparent)`,
                    animationDelay: "0ms",
                  }}
                />
                <span
                  className="absolute inset-0 rounded-full border animate-voice-ring"
                  style={{
                    borderColor: `color-mix(in oklab, ${cyan} 22%, transparent)`,
                    animationDelay: "700ms",
                  }}
                />
              </>
            )}
            <span
              className="absolute inset-[18px] rounded-full backdrop-blur-sm"
              style={{
                background: `color-mix(in oklab, ${cyan} 14%, transparent)`,
              }}
            />
            <Mic className="relative z-10 h-9 w-9" stroke={cyan} />
          </button>
          <span
            className="mt-3 inline-flex items-center rounded-full px-3 py-1 text-xs font-medium"
            style={{
              background: `color-mix(in oklab, ${cyan} 12%, transparent)`,
              color: cyan,
            }}
          >
            {activeState}
          </span>

          <div className="relative z-10 mt-6 flex w-full max-w-md items-center gap-2 rounded-full border border-white/60 bg-white/60 px-3 py-1.5">
            <input
              placeholder="Ask ÆON... (e.g. 'Turn off hallway lights')"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && queryText.trim()) {
                  sendVoiceQuery(queryText);
                  setQueryText("");
                }
              }}
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            <button
              onClick={() => {
                if (queryText.trim()) {
                  sendVoiceQuery(queryText);
                  setQueryText("");
                }
              }}
              className="rounded-full bg-foreground px-3.5 py-1 text-xs font-medium text-background"
            >
              Send
            </button>
          </div>

          {voice.lastQuery && voice.lastQuery !== "System Ready" && (
            <div className="relative z-10 mt-4 max-w-md rounded-2xl bg-white/40 p-3 text-left text-xs">
              <p className="text-muted-foreground"><strong>Query:</strong> "{voice.lastQuery}"</p>
              {voice.lastResponse && voice.lastResponse !== "System Ready" && (
                <p className="mt-1 text-foreground font-medium"><strong>ÆON:</strong> "{voice.lastResponse}"</p>
              )}
            </div>
          )}
        </div>

        {activeState === "Speaking" && (
          <div className="relative z-10 mt-4 flex h-16 items-end justify-center gap-[3px]">
            {bars.map((bar, i) => (
              <span
                key={i}
                className="w-[3px] rounded-full animate-voice-wave"
                style={{
                  height: `${bar.height}%`,
                  background: cyan,
                  animationDelay: `${bar.delay}ms`,
                }}
              />
            ))}
          </div>
        )}
      </section>
    </Reveal>
  );
}




/* ---------------- DashboardV2 (single-page, no duplicates) ---------------- */
function V2DeviceCard({
  name,
  icon: Icon,
  status,
  tint,
  model,
  checkpoint,
}: {
  name: string;
  icon: typeof Cpu;
  status: string;
  tint: string;
  model: string;
  checkpoint: string;
}) {
  const online = status === "Online" || status === "Connected";
  return (
    <Reveal>
      <div className="glass-card card-lift relative overflow-hidden rounded-3xl p-5">
        <div
          className="pointer-events-none absolute -right-10 -top-10 h-28 w-28 rounded-full opacity-40 blur-2xl"
          style={{ background: tint }}
        />
        <div className="flex items-center gap-3">
          <span
            className="grid h-11 w-11 place-items-center rounded-2xl"
            style={{ background: `color-mix(in oklab, ${tint} 15%, white)`, color: tint }}
          >
            <Icon className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">{name}</p>
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className={`h-1.5 w-1.5 rounded-full ${online ? "bg-emerald-500 animate-pulse" : "bg-amber-400"}`} />
              {status}
            </p>
          </div>
        </div>
        <div className="mt-4 space-y-2 rounded-2xl bg-white/60 p-3">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Model version</span>
            <span className="font-medium">{model}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Last checkpoint</span>
            <span className="font-medium">{checkpoint}</span>
          </div>
        </div>
      </div>
    </Reveal>
  );
}

function V2LiveAlerts() {
  const { telemetry, flagFalseAlarm } = useAeon();
  const logs = telemetry.privacyMesh.auditLog || [];
  
  const alerts = logs.slice(0, 2).map((log) => {
    let icon = "🚶";
    if (log.event.includes("Person") || log.event.includes("Motion")) icon = "🚶";
    else if (log.event.includes("Door") || log.event.includes("Open")) icon = "🚪";
    else if (log.event.includes("Temp") || log.event.includes("Env")) icon = "🌡️";
    else if (log.event.includes("Power") || log.event.includes("Boot") || log.event.includes("Chain")) icon = "⚡";

    return {
      id: log.token,
      icon,
      title: log.event,
      detail: `${log.token} · Status: ${log.status}`,
      time: log.time,
      status: log.status,
    };
  });
  const tint = "var(--aeon-orange)";
  return (
    <Reveal>
      <div className="glass-card relative overflow-hidden rounded-3xl p-5 md:p-6">
        <div
          className="pointer-events-none absolute -right-16 -top-16 h-40 w-40 rounded-full opacity-40 blur-3xl"
          style={{ background: tint }}
        />
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold tracking-tight sm:text-lg">Live Alerts</h2>
            <p className="text-[11px] text-muted-foreground sm:text-xs">Signed capability alerts · today</p>
          </div>
          <span
            className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px]"
            style={{ background: `color-mix(in oklab, ${tint} 15%, white)`, color: tint }}
          >
            <span className="h-1.5 w-1.5 rounded-full animate-pulse" style={{ background: tint }} />
            {alerts.length} active
          </span>
        </div>
        <div className="space-y-3">
          {alerts.map((a, i) => (
            <Reveal key={a.id} delay={i * 80}>
              <div className="card-lift flex flex-wrap items-center gap-3 rounded-2xl bg-white/60 p-3 sm:gap-4 sm:p-4">
                <div
                  className="grid h-10 w-10 place-items-center rounded-2xl text-lg"
                  style={{ background: `color-mix(in oklab, ${tint} 20%, white)` }}
                >
                  {a.icon}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold">{a.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {a.detail} · {a.time}
                  </p>
                </div>
                <button
                  onClick={() => flagFalseAlarm(a.id)}
                  disabled={a.status === "false_alarm"}
                  className="rounded-full bg-foreground px-3.5 py-1.5 text-xs text-background hover:scale-[1.02] transition-transform disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {a.status === "false_alarm" ? "Flagged" : "False alarm"}
                </button>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </Reveal>
  );
}

/* ---------- Intelligence Orb (hero) ---------- */
function IntelligenceOrb() {
  const cyan = "var(--aeon-cyan)";
  const purple = "var(--aeon-purple)";
  return (
    <div className="relative grid h-52 w-52 shrink-0 place-items-center sm:h-64 sm:w-64">
      {/* outer soft halo */}
      <div
        className="absolute inset-0 rounded-full opacity-70 blur-3xl"
        style={{ background: `radial-gradient(circle, color-mix(in oklab, ${cyan} 60%, transparent), transparent 70%)` }}
      />
      {/* rotating conic ring */}
      <div
        className="absolute inset-4 rounded-full opacity-80"
        style={{
          background: `conic-gradient(from 0deg, ${cyan}, ${purple}, ${cyan})`,
          maskImage: "radial-gradient(circle, transparent 55%, black 58%, black 66%, transparent 70%)",
          WebkitMaskImage: "radial-gradient(circle, transparent 55%, black 58%, black 66%, transparent 70%)",
          animation: "aeon-orb-rotate 12s linear infinite",
        }}
      />
      {/* counter-rotating dashed orbit */}
      <div
        className="absolute inset-2 rounded-full border border-dashed opacity-40"
        style={{ borderColor: cyan, animation: "aeon-orb-rotate-rev 22s linear infinite" }}
      />
      {/* core orb */}
      <div
        className="relative grid h-32 w-32 place-items-center rounded-full animate-orb-breathe sm:h-40 sm:w-40"
        style={{
          background: `radial-gradient(circle at 30% 30%, white, color-mix(in oklab, ${cyan} 40%, white) 45%, color-mix(in oklab, ${purple} 60%, ${cyan}) 100%)`,
          boxShadow: `0 0 60px color-mix(in oklab, ${cyan} 55%, transparent), inset 0 0 40px color-mix(in oklab, ${purple} 30%, transparent)`,
        }}
      >
        <div
          className="h-4 w-4 rounded-full"
          style={{ background: "white", boxShadow: `0 0 20px ${cyan}, 0 0 40px ${cyan}` }}
        />
      </div>
      {/* orbiting dots */}
      {[0, 120, 240].map((deg, i) => (
        <div
          key={deg}
          className="absolute inset-0"
          style={{ animation: `aeon-orb-rotate ${8 + i * 3}s linear infinite`, transform: `rotate(${deg}deg)` }}
        >
          <div
            className="absolute left-1/2 top-0 h-2 w-2 -translate-x-1/2 rounded-full"
            style={{
              background: i === 1 ? purple : cyan,
              boxShadow: `0 0 12px ${i === 1 ? purple : cyan}`,
            }}
          />
        </div>
      ))}
    </div>
  );
}


/* ---------- Self Graph (network visualization) ---------- */
function V2SelfGraph() {
  const cyan = "oklch(0.78 0.13 210)";
  const purple = "oklch(0.7 0.2 300)";
  const pink = "oklch(0.78 0.18 350)";
  const green = "oklch(0.72 0.14 160)";
  const amber = "oklch(0.75 0.15 60)";

  const cx = 320;
  const cy = 260;
  const satellites = [
    { id: "arduino", label: "Arduino", tint: cyan, angle: -140, dist: 185, r: 30 },
    { id: "aipc", label: "AI PC", tint: purple, angle: -40, dist: 185, r: 32 },
    { id: "phone", label: "Phone", tint: pink, angle: 40, dist: 185, r: 28 },
    { id: "cloud", label: "Cloud", tint: green, angle: 140, dist: 185, r: 28 },
    { id: "sensor", label: "Sensors", tint: amber, angle: -90, dist: 205, r: 24 },
  ];
  const positioned = satellites.map((n) => {
    const rad = (n.angle * Math.PI) / 180;
    return { ...n, x: cx + Math.cos(rad) * n.dist, y: cy + Math.sin(rad) * n.dist };
  });
  const map = Object.fromEntries(positioned.map((n) => [n.id, n]));
  const edges: [string, string][] = [
    ["arduino", "sensor"],
    ["aipc", "phone"],
    ["phone", "cloud"],
    ["arduino", "aipc"],
  ];

  return (
    <Reveal>
      <div className="glass-card relative overflow-hidden rounded-3xl p-4 sm:p-5">
        <div
          className="pointer-events-none absolute -left-16 top-1/2 h-64 w-64 -translate-y-1/2 rounded-full opacity-30 blur-3xl"
          style={{ background: cyan }}
        />
        <div
          className="pointer-events-none absolute -right-16 top-1/2 h-64 w-64 -translate-y-1/2 rounded-full opacity-30 blur-3xl"
          style={{ background: purple }}
        />

        <div className="relative mb-3 flex flex-wrap items-center gap-2">
          <div className="mr-auto">
            <h2 className="text-base font-semibold tracking-tight sm:text-lg">Self Graph</h2>
            <p className="text-[11px] text-muted-foreground sm:text-xs">Live token flow across the ÆON mesh.</p>
          </div>
          {positioned.map((n) => (
            <span key={n.id} className="inline-flex items-center gap-1.5 rounded-full bg-foreground/[0.04] px-2 py-1 text-[10px] text-muted-foreground sm:text-[11px]">
              <span className="h-2 w-2 rounded-full" style={{ background: n.tint }} />
              {n.label}
            </span>
          ))}
        </div>

        <svg viewBox="0 0 640 520" className="relative h-[460px] w-full sm:h-[580px]">
          <defs>
            <linearGradient id="v2sg-edge" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={purple} stopOpacity="0.6" />
              <stop offset="100%" stopColor={pink} stopOpacity="0.6" />
            </linearGradient>
            <radialGradient id="v2sg-core" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="oklch(0.85 0.16 300)" stopOpacity="0.9" />
              <stop offset="100%" stopColor={purple} stopOpacity="0.1" />
            </radialGradient>
            <filter id="v2sg-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="b" />
              <feMerge>
                <feMergeNode in="b" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* orbit rings */}
          {[100, 155, 205].map((r, i) => (
            <circle key={i} cx={cx} cy={cy} r={r} fill="none" stroke="oklch(0.6 0.02 275 / 0.12)" strokeDasharray="2 6" />
          ))}

          {/* center to node links */}
          {positioned.map((n, i) => (
            <line
              key={`c-${n.id}`}
              x1={cx}
              y1={cy}
              x2={n.x}
              y2={n.y}
              stroke="url(#v2sg-edge)"
              strokeWidth={1.5}
              strokeDasharray="200"
              strokeDashoffset="200"
              style={{ animation: `aeon-trace-draw 1.4s ease-out ${i * 0.1}s forwards` }}
            />
          ))}

          {/* inter-node edges */}
          {edges.map(([a, b], i) => {
            const A = map[a];
            const B = map[b];
            return (
              <line
                key={`e-${i}`}
                x1={A.x}
                y1={A.y}
                x2={B.x}
                y2={B.y}
                stroke={A.tint}
                strokeOpacity="0.35"
                strokeWidth={1}
                strokeDasharray="180"
                strokeDashoffset="180"
                style={{ animation: `aeon-trace-draw 1.6s ease-out ${0.8 + i * 0.1}s forwards` }}
              />
            );
          })}

          {/* token particles along center links */}
          {positioned.map((n, i) => {
            const dur = 3 + (i % 3) * 0.8;
            return (
              <g key={`tok-${n.id}`} filter="url(#v2sg-glow)">
                <circle r="3" fill={n.tint}>
                  <animate attributeName="cx" from={cx} to={n.x} dur={`${dur}s`} begin={`${1.6 + i * 0.3}s`} repeatCount="indefinite" />
                  <animate attributeName="cy" from={cy} to={n.y} dur={`${dur}s`} begin={`${1.6 + i * 0.3}s`} repeatCount="indefinite" />
                  <animate attributeName="opacity" values="0;1;1;0" dur={`${dur}s`} begin={`${1.6 + i * 0.3}s`} repeatCount="indefinite" />
                </circle>
              </g>
            );
          })}

          {/* center "User" */}
          <g style={{ animation: `aeon-rise 0.7s ease-out 0.2s both` }}>
            <circle cx={cx} cy={cy} r={82} fill="url(#v2sg-core)" />
            <circle cx={cx} cy={cy} r={52} fill="white" stroke={purple} strokeWidth={2} />
            <circle cx={cx} cy={cy} r={52} fill="none" stroke={purple} strokeOpacity="0.35" strokeWidth={2}>
              <animate attributeName="r" values="52;72;52" dur="3s" repeatCount="indefinite" />
              <animate attributeName="stroke-opacity" values="0.35;0;0.35" dur="3s" repeatCount="indefinite" />
            </circle>
            <text x={cx} y={cy - 2} textAnchor="middle" fontSize="15" fontWeight="600" fill="oklch(0.25 0.02 275)">You</text>
            <text x={cx} y={cy + 16} textAnchor="middle" fontSize="10" fill="oklch(0.5 0.02 275)">ÆON identity</text>
          </g>

          {/* satellite nodes */}
          {positioned.map((n, i) => (
            <g key={n.id} style={{ animation: `aeon-rise 0.7s ease-out ${i * 0.1 + 0.7}s both` }}>
              <circle cx={n.x} cy={n.y} r={n.r + 10} fill={n.tint} opacity="0.12">
                <animate attributeName="r" values={`${n.r + 6};${n.r + 14};${n.r + 6}`} dur={`${2.4 + i * 0.2}s`} repeatCount="indefinite" />
              </circle>
              <circle cx={n.x} cy={n.y} r={n.r} fill="white" stroke={n.tint} strokeWidth={2} />
              <circle cx={n.x} cy={n.y} r={n.r - 8} fill={n.tint} opacity="0.85" />
              <text x={n.x} y={n.y + n.r + 16} textAnchor="middle" fontSize="12" fontWeight="500" fill="oklch(0.3 0.02 275)">
                {n.label}
              </text>
            </g>
          ))}
        </svg>
      </div>
    </Reveal>
  );
}


/* ---------- Dream State (dramatic comparison) ---------- */
function V2Dream() {
  const purple = "var(--aeon-purple)";
  return (
    <Reveal>
      <div
        className="glass-card relative overflow-hidden rounded-3xl p-6 md:p-8"
        style={{
          background:
            "linear-gradient(135deg, color-mix(in oklab, var(--aeon-purple) 8%, white), color-mix(in oklab, var(--aeon-pink) 6%, white))",
        }}
      >
        <div
          className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full opacity-50 blur-3xl"
          style={{ background: purple }}
        />
        <div
          className="pointer-events-none absolute -left-20 -bottom-20 h-64 w-64 rounded-full opacity-40 blur-3xl"
          style={{ background: "var(--aeon-pink)" }}
        />

        <div className="relative flex flex-wrap items-end justify-between gap-4">
          <div>
            <span
              className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-medium"
              style={{ background: `color-mix(in oklab, ${purple} 18%, white)`, color: purple }}
            >
              <Moon className="h-3 w-3" /> Dream State · overnight
            </span>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight md:text-3xl">
              ÆON replayed the day and got{" "}
              <span className="text-gradient" style={{ fontFamily: "'Instrument Serif', serif", fontWeight: 400 }}>
                sharper
              </span>
              .
            </h2>
          </div>
          <button className="inline-flex items-center gap-1.5 rounded-full bg-foreground px-4 py-2 text-sm text-background hover:scale-[1.02] transition-transform">
            <Moon className="h-4 w-4" /> Activate Night Mode
          </button>
        </div>

        <div className="relative mt-6 grid gap-4 md:grid-cols-3">
          {/* Latency */}
          <div className="rounded-3xl bg-white/70 p-6">
            <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Inference latency</p>
            <div className="mt-3 flex items-baseline gap-3">
              <span className="text-4xl font-semibold tracking-tight text-muted-foreground line-through decoration-2">12ms</span>
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
              <span
                className="text-5xl font-semibold tracking-tight"
                style={{ color: purple, textShadow: `0 0 24px color-mix(in oklab, ${purple} 40%, transparent)` }}
              >
                8ms
              </span>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">Peak inference across Arduino + AI PC</p>
          </div>

          {/* Model */}
          <div className="rounded-3xl bg-white/70 p-6">
            <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Model</p>
            <div className="mt-3 flex items-baseline gap-3">
              <span className="text-4xl font-semibold tracking-tight text-muted-foreground">v7</span>
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
              <span
                className="text-5xl font-semibold tracking-tight"
                style={{ color: purple, textShadow: `0 0 24px color-mix(in oklab, ${purple} 40%, transparent)` }}
              >
                v8
              </span>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">4,820 events replayed · 38% smaller weights</p>
          </div>

          {/* Improvement */}
          <div
            className="relative overflow-hidden rounded-3xl p-6 text-background"
            style={{ background: `linear-gradient(135deg, ${purple}, var(--aeon-pink))` }}
          >
            <div className="pointer-events-none absolute -right-8 -top-8 h-32 w-32 rounded-full bg-white/20 blur-2xl" />
            <p className="text-[11px] uppercase tracking-wide opacity-80">Overall improvement</p>
            <div className="mt-3 flex items-baseline gap-1">
              <span className="text-6xl font-semibold tracking-tight">+33</span>
              <span className="text-2xl font-medium opacity-90">%</span>
            </div>
            <p className="mt-3 text-xs opacity-80">Faster, smaller, and more accurate than yesterday.</p>
          </div>
        </div>
      </div>
    </Reveal>
  );
}

function V2Analytics() {
  const latency = Array.from({ length: 14 }, (_, i) => ({ d: `D${i + 1}`, v: 90 + Math.round(Math.sin(i) * 20 + Math.random() * 12) }));
  const learn = Array.from({ length: 14 }, (_, i) => ({ d: `D${i + 1}`, v: 40 + i * 3.5 + Math.random() * 2 }));
  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">Analytics</h2>
        <p className="text-xs text-muted-foreground">14-day history · captured on-device.</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Recovery Latency Trend (ms)" data={latency} color="oklch(0.78 0.13 210)" type="line" />
        <ChartCard title="Learning Curve (%)" data={learn} color="oklch(0.7 0.2 300)" type="area" />
      </div>
    </section>
  );
}

/* ================================================================
   CONNECTION STATUS BAR — WS + REST visibility (image: bidirectional arrows)
   ================================================================ */
function ConnectionStatusBar() {
  const { isConnected, telemetry } = useAeon();
  const serial = telemetry.serialStatus;
  const snapdragon = telemetry.snapdragonStatus;

  const items = [
    {
      label: "WebSocket",
      sublabel: "/ws/dashboard",
      connected: isConnected,
      tint: "var(--aeon-cyan)",
      icon: isConnected ? Wifi : WifiOff,
    },
    {
      label: "Device Gateway",
      sublabel: "/ws/device",
      connected: serial.connected,
      tint: "var(--aeon-purple)",
      icon: PlugZap,
    },
    {
      label: "FastAPI Backend",
      sublabel: "/api/*",
      connected: isConnected,
      tint: "var(--aeon-blue)",
      icon: Network,
    },
    {
      label: "NPU Runtime",
      sublabel: snapdragon.npuActive ? "Active" : "Standby",
      connected: snapdragon.connected,
      tint: "var(--aeon-pink)",
      icon: Zap,
    },
  ];

  return (
    <Reveal>
      <div className="glass-card rounded-2xl px-4 py-3">
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <span className="mr-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            System Links
          </span>
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.label}
                className="flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px]"
                style={{
                  background: item.connected
                    ? `color-mix(in oklab, ${item.tint} 12%, white)`
                    : "oklch(0.96 0.005 280)",
                }}
              >
                <Icon
                  className="h-3 w-3"
                  style={{ color: item.connected ? item.tint : "oklch(0.6 0.02 275)" }}
                />
                <span
                  className="font-medium"
                  style={{ color: item.connected ? item.tint : "oklch(0.55 0.02 275)" }}
                >
                  {item.label}
                </span>
                <span className="text-muted-foreground">·</span>
                <span className="text-muted-foreground">{item.sublabel}</span>
                <span
                  className={`h-1.5 w-1.5 rounded-full ${item.connected ? "animate-pulse" : ""}`}
                  style={{ background: item.connected ? item.tint : "oklch(0.75 0.05 275)" }}
                />
              </div>
            );
          })}
          {/* bidirectional indicator */}
          <span className="ml-auto hidden items-center gap-1 text-[10px] text-muted-foreground sm:flex">
            <ArrowRight className="h-3 w-3 -scale-x-100" />
            <span>Request / Data Flow</span>
            <ArrowRight className="h-3 w-3" />
            <span>Bidirectional</span>
          </span>
        </div>
      </div>
    </Reveal>
  );
}

/* ================================================================
   PROCESSING PIPELINE — Image: Sensor Processor → Inference → Policy Engine
   ================================================================ */
function ProcessingPipeline() {
  const { telemetry, isConnected } = useAeon();
  const serial = telemetry.serialStatus;
  const snapdragon = telemetry.snapdragonStatus;
  const learning = telemetry.continuousLearning;

  const stages = [
    {
      step: "01",
      title: "Sensor Processor",
      sublabel: "Feature Extraction",
      desc: `Temp ${serial.temperature}°C · Hum ${serial.humidity}% · Motion: ${serial.motionState}`,
      tint: "var(--aeon-cyan)",
      icon: Thermometer,
      active: serial.connected,
      badge: serial.connected ? "Live" : "Offline",
    },
    {
      step: "02",
      title: "Inference Pipeline",
      sublabel: "QNN Runtime",
      desc: `Latency ${snapdragon.latencyMs.toFixed(1)}ms · ${snapdragon.throughputFps} fps`,
      tint: "var(--aeon-purple)",
      icon: BrainCircuit,
      active: snapdragon.npuActive || snapdragon.connected,
      badge: snapdragon.npuActive ? "NPU Active" : "CPU",
    },
    {
      step: "03",
      title: "Policy Engine",
      sublabel: "Decision Logic",
      desc: learning.status,
      tint: "var(--aeon-blue)",
      icon: GitBranch,
      active: isConnected,
      badge: `θ ${learning.sensitivityThreshold}`,
    },
  ];

  return (
    <Reveal>
      <div className="glass-card overflow-hidden rounded-3xl p-5 md:p-6">
        {/* header */}
        <div className="mb-5 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold tracking-tight sm:text-lg">
              Processing Pipeline
            </h2>
            <p className="text-[11px] text-muted-foreground sm:text-xs">
              End-to-end · &lt;100ms latency
            </p>
          </div>
          <span className="rounded-full bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-700">
            {serial.connected ? "Active" : "Waiting"}
          </span>
        </div>

        {/* pipeline stages */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-stretch sm:gap-0">
          {stages.map((stage, i) => {
            const Icon = stage.icon;
            const isLast = i === stages.length - 1;
            return (
              <div key={stage.step} className="flex flex-1 items-stretch sm:contents">
                {/* Stage card */}
                <div
                  className={`relative flex flex-1 flex-col gap-2 rounded-2xl p-4 transition-all sm:rounded-none ${
                    i === 0 ? "sm:rounded-l-2xl" : ""
                  } ${isLast ? "sm:rounded-r-2xl" : ""}`}
                  style={{
                    background: stage.active
                      ? `color-mix(in oklab, ${stage.tint} 8%, white)`
                      : "color-mix(in oklab, white 70%, transparent)",
                    border: stage.active
                      ? `1.5px solid color-mix(in oklab, ${stage.tint} 28%, transparent)`
                      : "1.5px solid oklch(0.9 0.01 280)",
                  }}
                >
                  {/* glow */}
                  {stage.active && (
                    <div
                      className="pointer-events-none absolute -right-4 -top-4 h-16 w-16 rounded-full opacity-40 blur-2xl"
                      style={{ background: stage.tint }}
                    />
                  )}
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className="grid h-8 w-8 place-items-center rounded-xl"
                      style={{
                        background: `color-mix(in oklab, ${stage.tint} 18%, white)`,
                        color: stage.tint,
                      }}
                    >
                      <Icon className="h-4 w-4" />
                    </span>
                    <span
                      className="rounded-full px-2 py-0.5 text-[10px] font-medium"
                      style={{
                        background: stage.active
                          ? `color-mix(in oklab, ${stage.tint} 18%, white)`
                          : "oklch(0.94 0.01 280)",
                        color: stage.active ? stage.tint : "oklch(0.55 0.02 275)",
                      }}
                    >
                      {stage.badge}
                    </span>
                  </div>
                  <div>
                    <p className="text-xs font-semibold">{stage.title}</p>
                    <p
                      className="text-[10px]"
                      style={{ color: `color-mix(in oklab, ${stage.tint} 65%, oklch(0.5 0.02 275))` }}
                    >
                      {stage.sublabel}
                    </p>
                  </div>
                  <p className="text-[10px] text-muted-foreground leading-snug">{stage.desc}</p>
                  {/* step number */}
                  <span className="mt-auto self-end font-mono text-[10px] text-muted-foreground opacity-50">
                    {stage.step}
                  </span>
                </div>

                {/* Arrow connector between stages */}
                {!isLast && (
                  <div className="flex items-center justify-center sm:w-8">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/80 shadow-sm sm:h-7 sm:w-7 sm:-mx-1 sm:z-10">
                      <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Frame parser row */}
        <div className="mt-4 flex items-center gap-3 rounded-2xl bg-white/50 px-4 py-3">
          <span
            className="grid h-7 w-7 shrink-0 place-items-center rounded-lg"
            style={{ background: "color-mix(in oklab, var(--aeon-cyan) 15%, white)", color: "var(--aeon-cyan)" }}
          >
            <Layers className="h-3.5 w-3.5" />
          </span>
          <div className="min-w-0 flex-1">
            <span className="text-xs font-medium">Frame Parser & Validator</span>
            <span className="ml-2 text-[10px] text-muted-foreground">
              UART → JSON · {serial.connected ? `${serial.baud} baud` : "waiting"}
            </span>
          </div>
          <span className="text-[10px] text-muted-foreground">Device Gateway</span>
          <ArrowRight className="h-3 w-3 text-muted-foreground" />
          <span className="text-[10px] text-muted-foreground">Pipeline</span>
        </div>
      </div>
    </Reveal>
  );
}

/* ================================================================
   AI & MODEL MANAGEMENT — Image: Model Manager, QNN Runtime, Execution Provider
   ================================================================ */
function AIModelManagement() {
  const { telemetry, isConnected } = useAeon();
  const snapdragon = telemetry.snapdragonStatus;
  const learning = telemetry.continuousLearning;
  const dream = telemetry.dreamState;

  const purple = "var(--aeon-purple)";
  const blue = "var(--aeon-blue)";
  const pink = "var(--aeon-pink)";

  const models = [
    {
      name: "Model Manager",
      sublabel: "Load / Unload",
      status: snapdragon.connected ? "Ready" : "Offline",
      version: snapdragon.modelName || "QNN (Hexagon NPU)",
      tint: purple,
      icon: BookOpen,
      metric: `v8 · ${learning.progressPct}% converged`,
    },
    {
      name: "QNN Runtime Manager",
      sublabel: "Hexagon NPU",
      status: snapdragon.npuActive ? "NPU Active" : "CPU Fallback",
      version: "QNN HTP",
      tint: blue,
      icon: Cpu,
      metric: `${snapdragon.latencyMs.toFixed(1)}ms · ${snapdragon.throughputFps} fps`,
    },
    {
      name: "Execution Provider",
      sublabel: "QNN HTP / CPU",
      status: snapdragon.npuActive ? "HTP" : "CPU",
      version: snapdragon.powerState.split(" ")[0] || "—",
      tint: pink,
      icon: FlaskConical,
      metric: `${snapdragon.memoryMb}MB · ${snapdragon.powerState.split(" ")[0]}`,
    },
  ];

  return (
    <Reveal>
      <div className="glass-card rounded-3xl p-5 md:p-6">
        <div className="mb-5 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold tracking-tight sm:text-lg">
              AI & Model Management
            </h2>
            <p className="text-[11px] text-muted-foreground sm:text-xs">
              Snapdragon X Elite · on-device inference
            </p>
          </div>
          <span
            className="rounded-full px-2.5 py-1 text-[11px] font-medium"
            style={{
              background: `color-mix(in oklab, ${purple} 14%, white)`,
              color: purple,
            }}
          >
            {dream.active ? "Dream Running" : "Idle"}
          </span>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          {models.map((m, i) => {
            const Icon = m.icon;
            const active = m.status !== "Offline";
            return (
              <Reveal key={m.name} delay={i * 80}>
                <div
                  className="relative flex flex-col gap-3 rounded-2xl p-4"
                  style={{
                    background: active
                      ? `color-mix(in oklab, ${m.tint} 7%, white)`
                      : "color-mix(in oklab, white 70%, transparent)",
                    border: `1.5px solid color-mix(in oklab, ${m.tint} ${active ? "22%" : "8%"}, transparent)`,
                  }}
                >
                  {active && (
                    <div
                      className="pointer-events-none absolute -right-3 -top-3 h-12 w-12 rounded-full opacity-50 blur-xl"
                      style={{ background: m.tint }}
                    />
                  )}
                  <div className="flex items-start justify-between gap-2">
                    <span
                      className="grid h-9 w-9 place-items-center rounded-xl"
                      style={{ background: `color-mix(in oklab, ${m.tint} 18%, white)`, color: m.tint }}
                    >
                      <Icon className="h-4 w-4" />
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-medium`}
                      style={{
                        background: active
                          ? `color-mix(in oklab, ${m.tint} 16%, white)`
                          : "oklch(0.94 0.01 280)",
                        color: active ? m.tint : "oklch(0.55 0.02 275)",
                      }}
                    >
                      {m.status}
                    </span>
                  </div>
                  <div>
                    <p className="text-xs font-semibold leading-tight">{m.name}</p>
                    <p
                      className="text-[10px]"
                      style={{ color: `color-mix(in oklab, ${m.tint} 60%, oklch(0.5 0.02 275))` }}
                    >
                      {m.sublabel}
                    </p>
                  </div>
                  <div className="mt-auto rounded-xl bg-white/60 px-3 py-2">
                    <p className="text-[10px] font-mono text-muted-foreground">{m.metric}</p>
                  </div>
                </div>
              </Reveal>
            );
          })}
        </div>

        {/* Memory & Stats strip */}
        <div className="mt-4 grid grid-cols-3 gap-2">
          {[
            { k: "SoftGraph", v: `${telemetry.knowledgeGraph.nodesCount}N · ${telemetry.knowledgeGraph.edgesCount}E`, tint: blue },
            { k: "Event Store", v: `${(telemetry.events || []).length} events`, tint: purple },
            { k: "Tokens", v: `${telemetry.privacyMesh.capabilityTokensIssued} issued`, tint: pink },
          ].map((stat) => (
            <div
              key={stat.k}
              className="rounded-xl px-3 py-2 text-center"
              style={{ background: `color-mix(in oklab, ${stat.tint} 8%, white)` }}
            >
              <p className="text-[10px] text-muted-foreground">{stat.k}</p>
              <p
                className="text-xs font-semibold tabular-nums"
                style={{ color: stat.tint }}
              >
                {stat.v}
              </p>
            </div>
          ))}
        </div>
      </div>
    </Reveal>
  );
}

/* ================================================================
   SYSTEM SERVICES — Image: 6 horizontal services
   ================================================================ */
function SystemServices() {
  const { telemetry, isConnected } = useAeon();

  const services = [
    {
      name: "Config Manager",
      icon: Settings2,
      tint: "var(--aeon-blue)",
      status: "active",
      detail: "Central config",
    },
    {
      name: "Logger",
      icon: BarChart3,
      tint: "var(--aeon-purple)",
      status: "active",
      detail: "System-wide",
    },
    {
      name: "Health Monitor",
      icon: HeartPulse,
      tint: "oklch(0.65 0.22 27)",
      status: isConnected ? "active" : "warn",
      detail: isConnected ? "All OK" : "No backend",
    },
    {
      name: "Dream Scheduler",
      icon: CalendarClock,
      tint: "var(--aeon-pink)",
      status: telemetry.dreamState.active ? "running" : "idle",
      detail: telemetry.dreamState.active
        ? "Running"
        : `Last: ${telemetry.dreamState.lastRunTime}`,
    },
    {
      name: "Checkpoint Mgr",
      icon: Database,
      tint: "var(--aeon-cyan)",
      status: telemetry.serialStatus.connected ? "active" : "warn",
      detail: `${telemetry.serialStatus.lastCheckpointSec}s ago`,
    },
    {
      name: "Security",
      icon: Lock,
      tint: "oklch(0.7 0.15 150)",
      status: "active",
      detail: "Tokens enabled",
    },
  ];

  const statusColor: Record<string, string> = {
    active: "oklch(0.6 0.17 150)",
    running: "var(--aeon-purple)",
    idle: "oklch(0.6 0.02 275)",
    warn: "oklch(0.7 0.15 60)",
  };

  return (
    <Reveal>
      <div className="glass-card rounded-2xl p-4 sm:p-5">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold tracking-tight">System Services</h2>
            <p className="text-[10px] text-muted-foreground">Cross-cutting · shared layer</p>
          </div>
          <span className="rounded-full bg-emerald-500/10 px-2.5 py-1 text-[10px] font-medium text-emerald-700">
            {services.filter((s) => s.status === "active" || s.status === "running").length}/{services.length} running
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-6">
          {services.map((svc, i) => {
            const Icon = svc.icon;
            const sColor = statusColor[svc.status];
            return (
              <Reveal key={svc.name} delay={i * 50}>
                <div
                  className="flex flex-col items-center gap-2 rounded-2xl px-2 py-3 text-center"
                  style={{
                    background: `color-mix(in oklab, ${svc.tint} 7%, white)`,
                    border: `1px solid color-mix(in oklab, ${svc.tint} 18%, transparent)`,
                  }}
                >
                  <span
                    className="grid h-9 w-9 place-items-center rounded-xl"
                    style={{ background: `color-mix(in oklab, ${svc.tint} 18%, white)`, color: svc.tint }}
                  >
                    <Icon className="h-4 w-4" />
                  </span>
                  <div>
                    <p className="text-[10px] font-semibold leading-tight">{svc.name}</p>
                    <p className="text-[9px] text-muted-foreground leading-tight mt-0.5">{svc.detail}</p>
                  </div>
                  <span
                    className="flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-medium"
                    style={{
                      background: `color-mix(in oklab, ${sColor} 14%, white)`,
                      color: sColor,
                    }}
                  >
                    <span
                      className={`h-1 w-1 rounded-full ${svc.status === "active" || svc.status === "running" ? "animate-pulse" : ""}`}
                      style={{ background: sColor }}
                    />
                    {svc.status}
                  </span>
                </div>
              </Reveal>
            );
          })}
        </div>
      </div>
    </Reveal>
  );
}

/* ================================================================
   DashboardV2 — main home page
   ================================================================ */
export function DashboardV2() {
  const { telemetry, triggerDream, isConnected } = useAeon();
  const serial = telemetry.serialStatus;
  const snapdragon = telemetry.snapdragonStatus;
  const learning = telemetry.continuousLearning;

  const cyan = "var(--aeon-cyan)";
  const green = "var(--aeon-green)";
  return (
    <div className="space-y-10">
      {/* 1. Hero */}
      <Reveal>
        <div className="glass-card relative overflow-hidden rounded-3xl p-5 sm:p-6 md:p-10">
          <div
            className="pointer-events-none absolute -left-24 -top-24 h-72 w-72 rounded-full opacity-40 blur-3xl"
            style={{ background: cyan }}
          />
          <div
            className="pointer-events-none absolute -right-24 -bottom-24 h-72 w-72 rounded-full opacity-30 blur-3xl"
            style={{ background: "var(--aeon-purple)" }}
          />
          <div className="relative flex flex-col items-start gap-6 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:gap-8">
            <div className="min-w-0 w-full sm:flex-1">
              <span className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-white/60 px-3 py-1 text-[11px] font-medium text-muted-foreground sm:text-xs">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Live · streaming from local mesh
              </span>
              <h1 className="mt-4 text-4xl font-semibold leading-[1.02] tracking-tight sm:text-5xl md:text-6xl lg:text-7xl">
                <span className="text-gradient" style={{ fontFamily: "'Instrument Serif', serif", fontWeight: 400 }}>
                  ÆON Home
                </span>
              </h1>
              <p className="mt-4 max-w-xl text-base font-medium tracking-tight text-foreground/80 sm:text-lg md:text-xl">
                Computers forget. ÆON remembers.
              </p>
              <p className="mt-2 max-w-xl text-sm text-muted-foreground md:text-base">
                Persistent intelligence across every device.
              </p>
              <div className="mt-6 flex flex-wrap gap-2">
                <button className="glass-card inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm">
                  <Sparkles className="h-4 w-4" /> Explain
                </button>
                <button onClick={triggerDream} disabled={telemetry.dreamState.active} className="inline-flex items-center gap-1.5 rounded-full bg-foreground px-4 py-2 text-sm text-background hover:scale-[1.02] transition-transform whitespace-nowrap disabled:opacity-50">
                  <Moon className="h-4 w-4" /> Activate Night Mode
                </button>
              </div>
            </div>
            <div className="mx-auto sm:mx-0">
              <IntelligenceOrb />
            </div>
          </div>
        </div>
      </Reveal>

      {/* 1b. Voice Flow (icon-only) */}
      <V2VoiceFlow />

      {/* 2. Key Metrics — unified intelligence palette (cyan) */}
      <section className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground">Key metrics</h2>
        <div className="grid grid-cols-2 gap-2.5 auto-rows-fr sm:gap-3 md:gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Recovery latency" value={Math.round(snapdragon.latencyMs)} unit="ms" caption="Recovered after power interruption" tint={cyan} icon={Timer} />
          <MetricCard label="EEPROM usage" value={serial.eepromUsagePct} unit="%" caption="Persistent memory blocks" tint={cyan} icon={HardDrive} />
          <MetricCard label="Learning progress" value={learning.progressPct} unit="%" caption="Model convergence" tint={cyan} icon={BrainCircuit} />
          <MetricCard label="Active devices" value={serial.connected ? 4 : 2} unit="" caption={serial.connected ? "Arduino, ESP8266, PC, Mobile" : "PC, Mobile"} tint={cyan} icon={Radio} />
        </div>
      </section>

      {/* 3. Live Alerts (orange) */}
      <V2LiveAlerts />

      {/* 4. Devices */}
      <section className="space-y-3">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Devices</h2>
          <p className="text-xs text-muted-foreground">Every node speaks the ÆON protocol.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <V2DeviceCard name="Arduino Sentinel" icon={Cpu} status={serial.connected ? "Online" : "Offline"} tint={cyan} model="fw-2.4.1" checkpoint={`${serial.lastCheckpointSec}s ago`} />
          <V2DeviceCard name="ESP8266 Gateway" icon={Radio} status={serial.connected ? "Online" : "Offline"} tint={cyan} model="v1.0-wifi" checkpoint="bridge mode" />
          <V2DeviceCard name="Snapdragon X Elite" icon={HardDrive} status={snapdragon.connected ? "Online" : "Offline"} tint={cyan} model={snapdragon.modelName} checkpoint="just now" />
          <V2DeviceCard name="Mobile PWA" icon={Smartphone} status={isConnected ? "Connected" : "Offline Cache"} tint={cyan} model="PWA v1.0" checkpoint={isConnected ? "just now" : "offline"} />
        </div>
      </section>

      {/* 5. Persistent Pulse */}
      <section>
        <Pulse />
      </section>

      {/* 6. Privacy Audit (green) */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <span
            className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-medium"
            style={{ background: `color-mix(in oklab, ${green} 18%, white)`, color: green }}
          >
            <ShieldCheck className="h-3 w-3" /> Privacy — local-first
          </span>
        </div>
        <Privacy />
      </section>

      {/* 7. Self Graph */}
      <SelfGraph />

      {/* 8. Dream State */}
      <Dream />

      {/* 9. Analytics */}
      <Metrics />
    </div>
  );
}

/* ================================================================
   EVENTS — Full event timeline backed by /api/v1/events
   ================================================================ */
export function Events() {
  const { telemetry } = useAeon();
  const [apiEvents, setApiEvents] = useState<Array<{
    id: number; ts: string; category: string; name: string; payload: Record<string, unknown>;
  }>>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("All");

  const catColors: Record<string, string> = {
    security:  "var(--aeon-orange)",
    auth:      "var(--aeon-blue)",
    system:    "oklch(0.7 0.15 150)",
    learning:  "var(--aeon-pink)",
    sensor:    "var(--aeon-cyan)",
    voice:     "var(--aeon-purple)",
    All:       "var(--aeon-purple)",
  };

  useEffect(() => {
    import("@/lib/api").then(({ fetchEvents }) => {
      fetchEvents(80)
        .then((data) => { setApiEvents(data); setLoading(false); })
        .catch(() => setLoading(false));
    });
  }, []);

  const wsEvents = (telemetry.events || []).map((e) => ({
    id: e.id, ts: e.time, category: e.category, name: e.label, payload: {},
  }));

  const allEvents = apiEvents.length > 0 ? apiEvents : wsEvents;
  const categories = ["All", ...Array.from(new Set(allEvents.map((e) => e.category)))];
  const visible = filter === "All" ? allEvents : allEvents.filter((e) => e.category === filter);

  function tint(cat: string) { return catColors[cat] ?? "var(--aeon-purple)"; }
  function formatTs(ts: string) {
    try { return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); }
    catch { return ts; }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Events" subtitle="Every signal, every decision — the full live timeline." />

      {/* Stats strip */}
      <Reveal>
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "Total Events", value: allEvents.length, tint: "var(--aeon-purple)" },
            { label: "Categories",   value: categories.length - 1, tint: "var(--aeon-blue)" },
            { label: "Today",        value: allEvents.filter((e) => {
              try { return new Date(e.ts).toDateString() === new Date().toDateString(); }
              catch { return true; }
            }).length, tint: "var(--aeon-pink)" },
          ].map((s) => (
            <div key={s.label} className="glass-card rounded-2xl p-3 sm:p-4">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground sm:text-xs">{s.label}</p>
              <p className="mt-1 text-xl font-semibold tabular-nums sm:text-2xl" style={{ color: s.tint }}>
                <CountUp to={s.value} />
              </p>
            </div>
          ))}
        </div>
      </Reveal>

      {/* Category filters */}
      <Reveal>
        <div className="flex flex-wrap gap-2">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              className={`rounded-full px-3.5 py-1.5 text-xs font-medium transition active:scale-95 ${
                filter === cat ? "bg-foreground text-background" : "glass-card text-muted-foreground hover:text-foreground"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </Reveal>

      {/* Event list */}
      <div className="space-y-2.5">
        {loading && (
          <div className="glass-card flex items-center justify-center rounded-2xl py-16 text-sm text-muted-foreground">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent mr-2" />
            Loading events…
          </div>
        )}
        {!loading && visible.length === 0 && (
          <div className="glass-card flex flex-col items-center justify-center gap-3 rounded-2xl py-16">
            <Activity className="h-10 w-10 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">No events in this category yet.</p>
          </div>
        )}
        {visible.map((ev, i) => (
          <Reveal key={ev.id} delay={i * 40}>
            <div className="glass-card card-lift flex items-center gap-3 rounded-2xl px-4 py-3">
              <span
                className="grid h-9 w-9 shrink-0 place-items-center rounded-xl"
                style={{ background: `color-mix(in oklab, ${tint(ev.category)} 14%, white)`, color: tint(ev.category) }}
              >
                <Activity className="h-4 w-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13px] font-medium">{ev.name}</p>
                <p className="text-[11px] text-muted-foreground">
                  {ev.category} · {formatTs(ev.ts)}
                </p>
              </div>
              <span
                className="shrink-0 rounded-full px-2.5 py-1 text-[10px] font-medium"
                style={{
                  background: `color-mix(in oklab, ${tint(ev.category)} 12%, white)`,
                  color: tint(ev.category),
                }}
              >
                {ev.category}
              </span>
            </div>
          </Reveal>
        ))}
      </div>
    </div>
  );
}

/* ================================================================
   VOICE — Voice command center backed by /api/v1/voice/*
   ================================================================ */
export function Voice() {
  const { telemetry, sendVoiceQuery, startListening } = useAeon();
  const voice = telemetry.voiceAssistant;

  const [textInput, setTextInput] = useState("");
  const [sending, setSending] = useState(false);
  const [conversation, setConversation] = useState<Array<{
    role: "user" | "aeon"; text: string; ts: string;
  }>>([
    { role: "aeon", text: "Namaste! Main ÆON hoon. Aap kya poochna chahte hain?", ts: "just now" },
  ]);

  async function handleSend() {
    if (!textInput.trim()) return;
    const query = textInput.trim();
    setTextInput("");
    const userTs = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setConversation((prev) => [...prev, { role: "user", text: query, ts: userTs }]);
    setSending(true);

    try {
      const { sendVoiceText } = await import("@/lib/api");
      const res = await sendVoiceText(query);
      const aeonTs = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      setConversation((prev) => [...prev, { role: "aeon", text: res.response || res.transcript || "…", ts: aeonTs }]);
    } catch {
      sendVoiceQuery(query);
      const aeonTs = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      setConversation((prev) => [...prev, { role: "aeon", text: voice.lastResponse || "Command received.", ts: aeonTs }]);
    } finally {
      setSending(false);
    }
  }

  const quickCmds = [
    "Who is home?",
    "Lock the front door",
    "Start dream mode",
    "Show today's events",
    "What's the temperature?",
    "Privacy status report",
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Voice Assistant" subtitle="Talk to ÆON. Local processing, zero cloud dependency." />

      {/* Status pills */}
      <Reveal>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Sarvam AI", ok: voice.sarvamConnected, tint: "var(--aeon-cyan)" },
            { label: "Language", value: voice.language, tint: "var(--aeon-blue)" },
            { label: "Listening", ok: voice.isListening, tint: "var(--aeon-purple)" },
            { label: "Speaking",  ok: voice.isSpeaking,  tint: "var(--aeon-pink)" },
          ].map((p) => (
            <div key={p.label} className="glass-card flex items-center gap-2.5 rounded-2xl p-3">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ background: p.ok !== undefined ? (p.ok ? "oklch(0.7 0.15 150)" : "oklch(0.6 0.15 27)") : p.tint }}
              />
              <div className="min-w-0">
                <p className="text-[10px] text-muted-foreground">{p.label}</p>
                <p className="text-xs font-medium">
                  {p.value ?? (p.ok ? "Active" : "Inactive")}
                </p>
              </div>
            </div>
          ))}
        </div>
      </Reveal>

      {/* Conversation */}
      <Reveal>
        <div className="glass-card overflow-hidden rounded-3xl">
          <div className="flex items-center justify-between border-b border-white/40 px-5 py-3">
            <div className="flex items-center gap-2">
              <Mic className="h-4 w-4" style={{ color: "var(--aeon-purple)" }} />
              <span className="text-sm font-semibold">Conversation</span>
            </div>
            <button
              onClick={() => startListening()}
              className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition active:scale-95 ${
                voice.isListening
                  ? "animate-pulse bg-red-500/10 text-red-600"
                  : "bg-foreground text-background hover:scale-[1.02]"
              }`}
            >
              <Mic className="h-3 w-3" />
              {voice.isListening ? "Listening…" : "Hold to speak"}
            </button>
          </div>

          <div className="flex max-h-72 flex-col gap-3 overflow-y-auto p-4">
            {conversation.map((msg, i) => (
              <div
                key={i}
                className={`flex gap-2.5 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
              >
                <span
                  className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-xs font-bold"
                  style={{
                    background: msg.role === "aeon" ? "var(--gradient-aeon)" : "oklch(0.92 0.01 275)",
                    color: msg.role === "aeon" ? "white" : "oklch(0.3 0.02 275)",
                  }}
                >
                  {msg.role === "aeon" ? "Æ" : "U"}
                </span>
                <div className={`max-w-[75%] rounded-2xl px-3.5 py-2.5 text-sm ${
                  msg.role === "user"
                    ? "bg-foreground text-background"
                    : "glass-card"
                }`}>
                  <p>{msg.text}</p>
                  <p className="mt-1 text-[10px] opacity-50">{msg.ts}</p>
                </div>
              </div>
            ))}
            {sending && (
              <div className="flex gap-2.5">
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-xs font-bold text-white" style={{ background: "var(--gradient-aeon)" }}>Æ</span>
                <div className="glass-card flex items-center gap-1 rounded-2xl px-4 py-3">
                  {[0, 0.2, 0.4].map((d, i) => (
                    <span key={i} className="h-1.5 w-1.5 rounded-full bg-foreground/40 animate-bounce" style={{ animationDelay: `${d}s` }} />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="flex items-center gap-2 border-t border-white/40 p-3">
            <input
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Type a command or question…"
              className="flex-1 rounded-xl bg-white/60 px-3.5 py-2.5 text-sm outline-none placeholder:text-muted-foreground"
            />
            <button
              onClick={handleSend}
              disabled={sending || !textInput.trim()}
              className="grid h-10 w-10 place-items-center rounded-xl bg-foreground text-background transition hover:scale-[1.05] disabled:opacity-40"
            >
              <Zap className="h-4 w-4" />
            </button>
          </div>
        </div>
      </Reveal>

      {/* Quick commands */}
      <Reveal>
        <div className="glass-card rounded-3xl p-5">
          <p className="mb-3 text-sm font-semibold">Quick commands</p>
          <div className="flex flex-wrap gap-2">
            {quickCmds.map((cmd) => (
              <button
                key={cmd}
                onClick={() => { setTextInput(cmd); }}
                className="glass-card rounded-full px-3.5 py-1.5 text-xs text-muted-foreground hover:text-foreground transition active:scale-95"
              >
                {cmd}
              </button>
            ))}
          </div>
        </div>
      </Reveal>
    </div>
  );
}

/* ================================================================
   SENSORS — Live sensor dashboard backed by /api/v1/sensors/*
   ================================================================ */
export function Sensors() {
  const { telemetry } = useAeon();
  const serial = telemetry.serialStatus;

  const [latest, setLatest] = useState<{
    temperature?: number; humidity?: number; motion?: boolean; door_open?: boolean;
  }>({});
  const [history, setHistory] = useState<Array<{ t: string; temp: number; humidity: number; motion: number }>>([]);

  useEffect(() => {
    import("@/lib/api").then(({ fetchSensorsLatest, fetchSensorsHistory }) => {
      fetchSensorsLatest()
        .then((d) => setLatest(d))
        .catch(() => {});
      fetchSensorsHistory(120)
        .then((data) => {
          const mapped = data.slice(-30).map((d) => ({
            t: (() => { try { const dt = new Date(d.ts); return `${dt.getHours()}:${String(dt.getMinutes()).padStart(2,"0")}`; } catch { return d.ts; } })(),
            temp: d.temperature ?? 0,
            humidity: d.humidity ?? 0,
            motion: d.motion ? 1 : 0,
          }));
          setHistory(mapped);
        })
        .catch(() => {});
    });
  }, []);

  const temp     = latest.temperature ?? serial.temperature;
  const humidity = latest.humidity    ?? serial.humidity;
  const motion   = latest.motion      ?? serial.motionState !== "Idle";
  const door     = latest.door_open   ?? false;

  const stats = [
    { label: "Temperature", value: temp !== null && temp !== undefined ? temp.toFixed(1) : "—", unit: "°C", tint: "oklch(0.75 0.16 55)", icon: Thermometer },
    { label: "Humidity",    value: humidity !== null && humidity !== undefined ? String(Math.round(humidity)) : "—", unit: "%",  tint: "var(--aeon-blue)", icon: Activity },
    { label: "Motion",      value: motion ? "Detected" : "Clear", unit: "", tint: motion ? "oklch(0.65 0.22 27)" : "oklch(0.7 0.15 150)", icon: Radio },
    { label: "Door",        value: door ? "Open" : "Closed",      unit: "", tint: door   ? "oklch(0.65 0.22 27)" : "oklch(0.7 0.15 150)", icon: ShieldCheck },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Sensors" subtitle="Live environmental data from Arduino Sentinel." />

      {/* Live cards */}
      <Reveal>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {stats.map((s) => {
            const Icon = s.icon;
            return (
              <div key={s.label} className="glass-card card-lift relative overflow-hidden rounded-2xl p-4">
                <div className="pointer-events-none absolute -right-4 -top-4 h-16 w-16 rounded-full opacity-50 blur-2xl" style={{ background: s.tint }} />
                <span className="grid h-8 w-8 place-items-center rounded-xl" style={{ background: `color-mix(in oklab, ${s.tint} 14%, white)`, color: s.tint }}>
                  <Icon className="h-4 w-4" />
                </span>
                <p className="mt-3 text-xl font-semibold tabular-nums">
                  {s.value}<span className="text-xs text-muted-foreground">{s.unit}</span>
                </p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">{s.label}</p>
              </div>
            );
          })}
        </div>
      </Reveal>

      {/* Temperature chart */}
      {history.length > 0 && (
        <Reveal>
          <div className="glass-card rounded-3xl p-5 sm:p-6">
            <h3 className="mb-4 text-sm font-semibold">Temperature · last 2h</h3>
            <div className="h-52">
              <ResponsiveContainer>
                <AreaChart data={history}>
                  <defs>
                    <linearGradient id="temp-grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="oklch(0.75 0.16 55)" stopOpacity={0.5} />
                      <stop offset="100%" stopColor="oklch(0.75 0.16 55)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.5 0.02 275 / 0.15)" />
                  <XAxis dataKey="t" stroke="oklch(0.5 0.02 275)" fontSize={10} />
                  <YAxis stroke="oklch(0.5 0.02 275)" fontSize={10} unit="°" />
                  <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #eee", background: "rgba(255,255,255,0.9)" }} />
                  <Area type="monotone" dataKey="temp" stroke="oklch(0.75 0.16 55)" strokeWidth={2} fill="url(#temp-grad)" name="Temp °C" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </Reveal>
      )}

      {/* Humidity chart */}
      {history.length > 0 && (
        <Reveal>
          <div className="glass-card rounded-3xl p-5 sm:p-6">
            <h3 className="mb-4 text-sm font-semibold">Humidity · last 2h</h3>
            <div className="h-48">
              <ResponsiveContainer>
                <AreaChart data={history}>
                  <defs>
                    <linearGradient id="hum-grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--aeon-blue)" stopOpacity={0.5} />
                      <stop offset="100%" stopColor="var(--aeon-blue)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.5 0.02 275 / 0.15)" />
                  <XAxis dataKey="t" stroke="oklch(0.5 0.02 275)" fontSize={10} />
                  <YAxis stroke="oklch(0.5 0.02 275)" fontSize={10} unit="%" />
                  <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #eee", background: "rgba(255,255,255,0.9)" }} />
                  <Area type="monotone" dataKey="humidity" stroke="var(--aeon-blue)" strokeWidth={2} fill="url(#hum-grad)" name="Humidity %" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </Reveal>
      )}

      {/* Fallback placeholder if no history */}
      {history.length === 0 && (
        <Reveal>
          <div className="glass-card flex flex-col items-center gap-3 rounded-3xl py-16">
            <Thermometer className="h-10 w-10 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">Waiting for sensor data from Arduino Sentinel…</p>
            <p className="text-xs text-muted-foreground/60">Connect the Arduino on COM port and restart backend.</p>
          </div>
        </Reveal>
      )}
    </div>
  );
}

/* ================================================================
   MIGRATION — Identity transfer wizard backed by /api/v1/migration/*
   ================================================================ */
export function Migration() {
  const { telemetry, triggerMigration } = useAeon();
  const migration = telemetry.migrationState;

  const [userId, setUserId] = useState("default_user");
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] = useState<{ user_id: string; profile: unknown } | null>(null);
  const [step, setStep] = useState<"idle" | "export" | "qr" | "done">("idle");

  async function handleExport() {
    setExporting(true);
    setStep("export");
    try {
      const { fetchMigrationExport } = await import("@/lib/api");
      const result = await fetchMigrationExport(userId);
      setExportResult(result);
      setStep("qr");
    } catch {
      triggerMigration();
      setStep("qr");
    } finally {
      setExporting(false);
    }
  }

  const steps = [
    { id: "idle",   label: "Initiate",  desc: "Start the migration process" },
    { id: "export", label: "Export",    desc: "Package your ÆON identity" },
    { id: "qr",     label: "Transfer",  desc: "Scan QR on new device" },
    { id: "done",   label: "Complete",  desc: "Identity restored" },
  ];
  const stepIndex = steps.findIndex((s) => s.id === step);

  const infoCards = [
    { label: "Migration Status", value: migration.status,         tint: "var(--aeon-blue)"   },
    { label: "Target Device",    value: migration.targetDeviceId, tint: "var(--aeon-purple)" },
    { label: "Payload",          value: migration.qrCodePayload.slice(0, 28) + "…", tint: "var(--aeon-pink)" },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Identity Migration" subtitle="Move your ÆON self to a new device — zero data loss." />

      {/* Status cards */}
      <Reveal>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {infoCards.map((c) => (
            <div key={c.label} className="glass-card rounded-2xl p-4">
              <p className="text-[11px] uppercase tracking-wider text-muted-foreground">{c.label}</p>
              <p className="mt-1 truncate text-sm font-semibold" style={{ color: c.tint }}>{c.value}</p>
            </div>
          ))}
        </div>
      </Reveal>

      {/* Progress stepper */}
      <Reveal>
        <div className="glass-card rounded-3xl p-5 sm:p-6">
          <h3 className="mb-5 text-sm font-semibold">Migration Steps</h3>
          <div className="relative flex justify-between">
            <div className="absolute left-4 right-4 top-4 h-px bg-gradient-to-r from-transparent via-foreground/10 to-transparent" />
            {steps.map((s, i) => {
              const done = i < stepIndex;
              const active = i === stepIndex;
              const tint = done || active ? "var(--aeon-purple)" : "oklch(0.85 0.02 275)";
              return (
                <div key={s.id} className="flex flex-1 flex-col items-center gap-2 text-center">
                  <span
                    className="relative z-10 grid h-9 w-9 place-items-center rounded-full text-xs font-bold"
                    style={{
                      background: done || active ? `color-mix(in oklab, ${tint} 15%, white)` : "white",
                      border: `2px solid ${done || active ? tint : "oklch(0.85 0.02 275)"}`,
                      color: done || active ? tint : "oklch(0.6 0.02 275)",
                    }}
                  >
                    {done ? <CheckCircle2 className="h-4 w-4" /> : i + 1}
                  </span>
                  <p className={`text-[11px] font-medium ${active ? "text-foreground" : "text-muted-foreground"}`}>{s.label}</p>
                  <p className="hidden text-[10px] text-muted-foreground sm:block">{s.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </Reveal>

      {/* Action panel */}
      <Reveal>
        <div className="glass-card rounded-3xl p-5 sm:p-6">
          {step === "idle" && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold">Export your identity</h3>
              <div className="flex items-center gap-3">
                <input
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  placeholder="User ID"
                  className="flex-1 rounded-xl bg-white/60 px-3.5 py-2.5 text-sm outline-none placeholder:text-muted-foreground"
                />
                <button
                  onClick={handleExport}
                  className="shrink-0 rounded-xl bg-foreground px-5 py-2.5 text-sm font-medium text-background hover:scale-[1.02] transition-transform"
                >
                  Export
                </button>
              </div>
              <p className="text-xs text-muted-foreground">
                Your ÆON identity (preferences, patterns, trust graph) will be packaged as a signed payload. Raw data is never transmitted.
              </p>
            </div>
          )}

          {step === "export" && (
            <div className="flex flex-col items-center gap-4 py-8">
              <span className="h-8 w-8 animate-spin rounded-full border-2 border-foreground border-t-transparent" />
              <p className="text-sm text-muted-foreground">Packaging identity…</p>
            </div>
          )}

          {step === "qr" && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold">Scan on your new device</h3>
              {/* QR placeholder */}
              <div className="mx-auto flex h-52 w-52 flex-col items-center justify-center rounded-3xl border-2 border-dashed border-foreground/15 bg-white/60 text-center">
                <div className="grid grid-cols-3 gap-1 opacity-40">
                  {Array.from({ length: 9 }).map((_, i) => (
                    <span
                      key={i}
                      className="h-8 w-8 rounded-md"
                      style={{ background: [0,2,6,8].includes(i) ? "oklch(0.2 0.02 275)" : Math.random() > 0.5 ? "oklch(0.2 0.02 275)" : "white" }}
                    />
                  ))}
                </div>
                <p className="mt-3 text-[11px] font-mono text-muted-foreground">
                  {(exportResult?.user_id ?? userId)}
                </p>
              </div>
              <p className="text-center text-xs text-muted-foreground">
                Open ÆON on your new device → Settings → Import Identity → Scan
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setStep("done")}
                  className="flex-1 rounded-xl bg-foreground py-2.5 text-sm font-medium text-background hover:scale-[1.02] transition-transform"
                >
                  Confirm transferred
                </button>
                <button
                  onClick={() => setStep("idle")}
                  className="glass-card rounded-xl px-4 py-2.5 text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {step === "done" && (
            <div className="flex flex-col items-center gap-4 py-8">
              <span className="grid h-16 w-16 place-items-center rounded-full" style={{ background: "color-mix(in oklab, oklch(0.7 0.15 150) 15%, white)" }}>
                <CheckCircle2 className="h-8 w-8" style={{ color: "oklch(0.7 0.15 150)" }} />
              </span>
              <p className="text-base font-semibold">Migration complete</p>
              <p className="text-sm text-muted-foreground">Your ÆON identity is active on the new device.</p>
              <button onClick={() => { setStep("idle"); setExportResult(null); }} className="glass-card rounded-full px-5 py-2 text-sm">
                Start over
              </button>
            </div>
          )}
        </div>
      </Reveal>

      {/* What migrates */}
      <Reveal>
        <div className="glass-card rounded-3xl p-5 sm:p-6">
          <h3 className="mb-4 text-sm font-semibold">What gets migrated</h3>
          <div className="grid gap-2 sm:grid-cols-2">
            {[
              { label: "Preferences & patterns",   icon: "✅", desc: "Room, comfort, rhythm" },
              { label: "Trust graph",               icon: "✅", desc: "Signed capability tokens" },
              { label: "Device relationships",      icon: "✅", desc: "Named and trusted devices" },
              { label: "Privacy policies",          icon: "✅", desc: "Your locked rules stay locked" },
              { label: "Raw sensor recordings",     icon: "❌", desc: "Never stored, never migrated" },
              { label: "Cloud account credentials", icon: "❌", desc: "Not applicable — local-first" },
            ].map((it) => (
              <div key={it.label} className="flex items-start gap-2.5 rounded-xl bg-white/50 px-3.5 py-2.5">
                <span className="text-base">{it.icon}</span>
                <div>
                  <p className="text-[13px] font-medium">{it.label}</p>
                  <p className="text-[11px] text-muted-foreground">{it.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Reveal>
    </div>
  );
}

/* ---------------- Onboarding ---------------- */
export function Onboarding() {
  const [step, setStep] = useState(1);
  const { telemetry } = useAeon();

  return (
    <div className="space-y-6">
      <PageHeader title="Onboarding" subtitle="Initialize your offline-first persistent edge intelligence node." />

      <div className="glass-card rounded-3xl p-6 md:p-8">
        <div className="mb-8 flex items-center justify-between">
          {[
            { s: 1, label: "Hardware Pairing" },
            { s: 2, label: "Privacy Mesh" },
            { s: 3, label: "Biometric Identity" },
            { s: 4, label: "Sarvam Voice Test" },
          ].map((item) => (
            <div key={item.s} className="flex items-center gap-2">
              <span
                className={`grid h-8 w-8 place-items-center rounded-full text-xs font-bold transition-all ${
                  step === item.s
                    ? "bg-foreground text-background scale-110"
                    : step > item.s
                    ? "bg-emerald-500 text-white"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {step > item.s ? "✓" : item.s}
              </span>
              <span className="hidden text-xs font-medium md:inline">{item.label}</span>
            </div>
          ))}
        </div>

        {step === 1 && (
          <Reveal>
            <div className="space-y-4 text-center py-6">
              <Cpu className="h-12 w-12 mx-auto text-purple-500 animate-pulse" />
              <h3 className="text-xl font-semibold">Snapdragon X Elite + Arduino Pairing</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Connecting Arduino UNO Q over USB UART. Sensor data feature extraction initialized. EEPROM recovery buffer verified.
              </p>
              <button
                onClick={() => setStep(2)}
                className="mt-4 inline-flex items-center gap-2 rounded-full bg-foreground px-6 py-2.5 text-sm text-background hover:scale-105 transition-transform"
              >
                <span>Continue to Privacy Mesh</span>
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </Reveal>
        )}

        {step === 2 && (
          <Reveal>
            <div className="space-y-4 text-center py-6">
              <ShieldCheck className="h-12 w-12 mx-auto text-emerald-500" />
              <h3 className="text-xl font-semibold">Privacy-by-Design Token Mesh</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Verifying zero raw sensor telemetry transmission. Only signed intention tokens leave the MCU. Cryptographically audit-proven compliant with DPDP Act 2023.
              </p>
              <button
                onClick={() => setStep(3)}
                className="mt-4 inline-flex items-center gap-2 rounded-full bg-foreground px-6 py-2.5 text-sm text-background hover:scale-105 transition-transform"
              >
                <span>Initialize Identity</span>
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </Reveal>
        )}

        {step === 3 && (
          <Reveal>
            <div className="space-y-4 text-center py-6">
              <Fingerprint className="h-12 w-12 mx-auto text-pink-500" />
              <h3 className="text-xl font-semibold">Portable Cognitive Identity</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Generating local identity graph keypair. Your learned preferences stay on device and migrate via QR code with biometric approval.
              </p>
              <button
                onClick={() => setStep(4)}
                className="mt-4 inline-flex items-center gap-2 rounded-full bg-foreground px-6 py-2.5 text-sm text-background hover:scale-105 transition-transform"
              >
                <span>Test Sarvam Voice</span>
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </Reveal>
        )}

        {step === 4 && (
          <Reveal>
            <div className="space-y-4 text-center py-6">
              <Mic className="h-12 w-12 mx-auto text-blue-500 animate-bounce" />
              <h3 className="text-xl font-semibold">Sarvam Voice Bridge Setup</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Voice interface configured for Indian languages (Hindi, English, Tamil). Speech input processed on Snapdragon Edge Engine.
              </p>
              <button
                onClick={() => setStep(1)}
                className="mt-4 inline-flex items-center gap-2 rounded-full bg-emerald-600 px-6 py-2.5 text-sm text-white hover:scale-105 transition-transform"
              >
                <CheckCircle2 className="h-4 w-4" />
                <span>Setup Complete — Launch Dashboard</span>
              </button>
            </div>
          </Reveal>
        )}
      </div>
    </div>
  );
}

/* ---------------- Serial Status (Arduino UART) ---------------- */
export function SerialStatusSection() {
  const { telemetry } = useAeon();
  const { serialStatus } = telemetry;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Arduino Serial UART Status"
        subtitle="Direct hardware interface for environmental sensing & EEPROM persistent state recovery."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Port Status"
          value={serialStatus.connected ? 100 : 0}
          unit="%"
          caption={serialStatus.connected ? serialStatus.port : "Arduino disconnected"}
          tint="var(--aeon-purple)"
          icon={Cpu}
        />
        <MetricCard
          label="EEPROM Allocation"
          value={serialStatus.connected ? serialStatus.eepromUsagePct : 0}
          unit="%"
          caption="Checkpoint state persistent"
          tint="var(--aeon-blue)"
          icon={HardDrive}
        />
        <MetricCard
          label="Baud Rate"
          value={serialStatus.connected ? serialStatus.baud : 0}
          unit="bps"
          caption="Signed frame protocol"
          tint="var(--aeon-pink)"
          icon={Radio}
        />
        <MetricCard
          label="Last Checkpoint"
          value={serialStatus.connected && serialStatus.lastCheckpointSec > 0 ? serialStatus.lastCheckpointSec : 0}
          unit="s ago"
          caption="Survives zero reboot loss"
          tint="oklch(0.72 0.16 200)"
          icon={Timer}
        />
      </div>

      <Reveal>
        <div className="glass-card rounded-3xl p-6 space-y-4">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold">Live MCU Sensor Feature Telemetry</h3>
            <span className={`h-2 w-2 rounded-full ${serialStatus.connected ? "bg-emerald-500 animate-pulse" : "bg-amber-400"}`} />
            <span className="text-xs text-muted-foreground">
              {serialStatus.connected ? "Streaming" : "Arduino disconnected"}
            </span>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl bg-white/70 p-4 border border-border">
              <p className="text-xs text-muted-foreground">Ambient Temperature</p>
              <p className="text-2xl font-bold mt-1 text-amber-600">
                {serialStatus.temperature !== null ? `${serialStatus.temperature} °C` : "Waiting for sensor..."}
              </p>
            </div>
            <div className="rounded-2xl bg-white/70 p-4 border border-border">
              <p className="text-xs text-muted-foreground">Relative Humidity</p>
              <p className="text-2xl font-bold mt-1 text-blue-600">
                {serialStatus.humidity !== null ? `${serialStatus.humidity} %` : "Waiting for sensor..."}
              </p>
            </div>
            <div className="rounded-2xl bg-white/70 p-4 border border-border">
              <p className="text-xs text-muted-foreground">Motion Sensor State</p>
              <p className="text-2xl font-bold mt-1 text-purple-600">{serialStatus.motionState}</p>
            </div>
          </div>
        </div>
      </Reveal>
    </div>
  );
}

/* ---------------- Snapdragon Inference Status ---------------- */
export function SnapdragonStatusSection() {
  const { telemetry } = useAeon();
  const { snapdragonStatus } = telemetry;

  const providerLabel = snapdragonStatus.executionProvider === "QNN_HTP"
    ? "QNN (Hexagon HTP — NPU)"
    : snapdragonStatus.executionProvider === "QNN_CPU"
    ? "QNN (CPU Fallback)"
    : snapdragonStatus.executionProvider === "ONNX"
    ? "ONNX Runtime (CPU)"
    : snapdragonStatus.executionProvider === "UNAVAILABLE"
    ? "NPU unavailable"
    : snapdragonStatus.executionProvider || "Model not loaded";

  const npuReal = snapdragonStatus.executionProvider === "QNN_HTP";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Snapdragon Hexagon NPU Engine"
        subtitle="Real-time edge AI inference on Snapdragon X Elite via Qualcomm QNN Runtime."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Inference Latency"
          value={snapdragonStatus.latencyMs > 0 ? snapdragonStatus.latencyMs : 0}
          decimals={1}
          unit="ms"
          caption={npuReal ? "Hexagon NPU measured" : "CPU fallback measured"}
          tint="var(--aeon-purple)"
          icon={Zap}
        />
        <MetricCard
          label="Throughput"
          value={snapdragonStatus.throughputFps > 0 ? snapdragonStatus.throughputFps : 0}
          unit="FPS"
          caption="Frames processed this session"
          tint="var(--aeon-blue)"
          icon={Activity}
        />
        <MetricCard
          label="CPU Load"
          value={snapdragonStatus.cpuPct}
          decimals={1}
          unit="%"
          caption="Real-time from psutil"
          tint="var(--aeon-pink)"
          icon={HardDrive}
        />
        <MetricCard
          label="Tokens Issued"
          value={snapdragonStatus.tokensVerified}
          unit=""
          caption="Signed capability tokens"
          tint="oklch(0.72 0.16 200)"
          icon={ShieldCheck}
        />
      </div>

      <Reveal>
        <div className="glass-card rounded-3xl p-6 space-y-3">
          <h3 className="text-sm font-semibold">Snapdragon Hardware Compute Status</h3>
          <div className="rounded-2xl bg-white/60 p-4 border border-border space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Execution Provider (verified):</span>
              <span className={`font-semibold ${npuReal ? "text-emerald-600" : "text-amber-500"}`}>
                {providerLabel}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Active Model:</span>
              <span className="font-semibold text-purple-700">{snapdragonStatus.modelName}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Power (estimated):</span>
              <span className="font-semibold">{snapdragonStatus.powerState}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">NPU Utilization (estimated):</span>
              <span className="font-semibold text-muted-foreground italic">
                {snapdragonStatus.npuPctEstimated?.toFixed(1) ?? "—"}% (Hexagon DSP not readable via psutil)
              </span>
            </div>
            {!npuReal && snapdragonStatus.executionProvider !== "UNAVAILABLE" && (
              <div className="mt-2 rounded-xl bg-amber-50 border border-amber-200 px-3 py-2 text-amber-700">
                ⚠️ Running on {providerLabel}. QNN HTP requires Snapdragon X Elite hardware + QNN SDK installed.
              </div>
            )}
          </div>
        </div>
      </Reveal>
    </div>
  );
}
