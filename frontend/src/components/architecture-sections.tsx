import { useEffect, useState, Fragment } from "react";
import { useAeon } from "@/hooks/use-aeon-telemetry";
import { fetchMetricsSystem, fetchLearningStatus, type SystemMetrics, type LearningStatus } from "@/lib/api";
import {
  Layers,
  Cpu,
  GitBranch,
  Network,
  Zap,
  Database,
  BrainCircuit,
  Radio,
  AlertTriangle,
  Settings2,
  FileText,
  HeartPulse,
  CalendarClock,
  ShieldCheck,
  Lock,
  CheckCircle2,
  HardDrive,
  Thermometer,
  Activity,
  Cloud,
  RotateCcw,
  Wifi,
  Smartphone,
} from "lucide-react";
import { Reveal } from "@/components/Reveal";
import { useInView } from "@/hooks/use-in-view";

/* ─────────────────────────────────────────────────────────────────────────────
   StaleBanner — shown when WebSocket is disconnected
───────────────────────────────────────────────────────────────────────────── */
function StaleBanner() {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-amber-400/40 bg-amber-400/10 px-4 py-2.5 text-sm font-medium text-amber-600 dark:text-amber-300">
      <AlertTriangle className="h-4 w-4 shrink-0" />
      <span>⚠ Data may be stale — reconnecting…</span>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   StackNode — single component box with name, status dot, metric badge
───────────────────────────────────────────────────────────────────────────── */
interface StackNodeProps {
  name: string;
  sublabel?: string;
  status?: "online" | "idle" | "offline" | "unknown";
  metric?: string;
  onClick?: () => void;
}

export function StackNode({ name, sublabel, status = "unknown", metric, onClick }: StackNodeProps) {
  const dotClass =
    status === "online"
      ? "bg-emerald-500 animate-pulse"
      : status === "idle"
      ? "bg-amber-400"
      : status === "offline"
      ? "bg-red-500"
      : "bg-gray-300";

  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "flex w-full items-center gap-2 rounded-lg bg-white/60 px-2.5 py-1.5 text-left",
        "ring-1 ring-foreground/8 transition-all",
        onClick ? "cursor-pointer card-lift hover:bg-white/80" : "cursor-default",
      ].join(" ")}
    >
      {/* Name + sublabel */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-semibold leading-tight text-foreground">{name}</p>
        {sublabel && (
          <p className="truncate text-[10px] leading-tight text-muted-foreground">{sublabel}</p>
        )}
      </div>

      {/* Status dot + metric */}
      <div className="flex shrink-0 items-center gap-1.5">
        {metric && (
          <span className="rounded-full bg-foreground/8 px-1.5 py-0.5 text-[10px] font-medium tabular-nums text-foreground/70">
            {metric}
          </span>
        )}
        <span className={`h-2 w-2 rounded-full ${dotClass}`} />
      </div>
    </button>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   StackColumn — titled column wrapper with tint header
───────────────────────────────────────────────────────────────────────────── */
interface StackColumnProps {
  title: string;
  tint: string;
  children: React.ReactNode;
}

export function StackColumn({ title, tint, children }: StackColumnProps) {
  return (
    <div className="flex flex-col gap-1">
      {/* Tinted header label */}
      <p
        className="mb-0.5 px-1 text-[10px] font-semibold uppercase tracking-wider"
        style={{ color: tint }}
      >
        {title}
      </p>
      {/* Children stacked with small gaps */}
      <div className="flex flex-col gap-1">{children}</div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   SystemServicesBar — horizontal strip of 6 service chips
───────────────────────────────────────────────────────────────────────────── */
const SYSTEM_SERVICES = [
  { label: "Config Manager",          icon: Settings2     },
  { label: "Logger",                  icon: FileText      },
  { label: "Health Monitor",          icon: HeartPulse    },
  { label: "Dream State Scheduler",   icon: CalendarClock },
  { label: "Checkpoint Manager",      icon: ShieldCheck   },
  { label: "Security",                icon: Lock          },
] as const;

export function SystemServicesBar() {
  return (
    <div className="flex flex-wrap gap-2">
      {SYSTEM_SERVICES.map(({ label, icon: Icon }) => (
        <div
          key={label}
          className="glass-card flex items-center gap-1.5 rounded-lg px-2.5 py-1.5"
        >
          <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <span className="text-[11px] font-medium text-foreground/80">{label}</span>
        </div>
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   FlowArrow — animated SVG arrow with Request/Data Flow label
───────────────────────────────────────────────────────────────────────────── */
export function FlowArrow() {
  return (
    <div className="flex flex-col items-center gap-1">
      {/* Animated → arrow */}
      <svg
        width="32"
        height="16"
        viewBox="0 0 32 16"
        fill="none"
        aria-label="Request / Data Flow arrow"
      >
        <style>{`
          @keyframes drawArrow {
            from { stroke-dashoffset: 40; }
            to   { stroke-dashoffset: 0;  }
          }
          .flow-path {
            stroke-dasharray: 40;
            stroke-dashoffset: 40;
            animation: drawArrow 0.6s ease-out forwards;
          }
        `}</style>
        {/* Shaft */}
        <line
          className="flow-path"
          x1="2"
          y1="8"
          x2="28"
          y2="8"
          stroke="var(--aeon-blue)"
          strokeWidth="2"
          strokeLinecap="round"
        />
        {/* Arrowhead */}
        <polyline
          className="flow-path"
          points="22,3 29,8 22,13"
          stroke="var(--aeon-blue)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
      </svg>

      {/* Labels */}
      <span className="text-[10px] font-medium text-muted-foreground">Request / Data Flow</span>
      <span className="text-[10px] text-muted-foreground/60">↔ Bidirectional</span>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Panel 1 — SoftwareStackPanel
   Diagram 5: Software Architecture
───────────────────────────────────────────────────────────────────────────── */
const NODE_DETAILS: Record<string, { title: string; desc: string; config?: string }> = {
  "React UI Components": {
    title: "React UI Components",
    desc: "Vibrant, glassmorphic layout utilizing Tailwind CSS for smooth micro-animations. Built as modular, reusable components using Radix UI primitives.",
    config: "Path: frontend/src/components/ui/"
  },
  "Live Charts & Widgets": {
    title: "Live Charts & Widgets",
    desc: "Uses Recharts to display interactive time series visualizations of sensor trends (temperature, humidity) and EEPROM wear allocation without adding performance overhead.",
    config: "Telemetry Frequency: 1 Hz"
  },
  "WebSocket Client": {
    title: "WebSocket Client",
    desc: "A reactive client that establishes a persistent full-duplex WebSocket connection to the backend `/ws/dashboard` endpoint to receive live state updates.",
    config: "Reconnection Delay: 3000ms"
  },
  "REST API Client": {
    title: "REST API Client",
    desc: "A custom fetch wrapper used to make HTTP POST/GET requests for one-off operations like triggering models, saving checkpoints, or fetching historical graphs.",
    config: "Base URL: http://localhost:8000"
  },
  "Service Worker (PWA)": {
    title: "Service Worker (PWA)",
    desc: "Ensures the application is offline-first. Handles offline asset caching, page shells, and queues transactional REST updates when local Wi-Fi drops.",
    config: "Cache Name: aeon-home-pwa-v1"
  },
  "FastAPI Routers": {
    title: "FastAPI Routers",
    desc: "Python web API framework. Serves JSON payloads for sensor history, model actions, voice requests, and cryptographic audit proofs.",
    config: "Endpoints: /api/v1/health, /api/v1/sensors/*"
  },
  "WebSocketBus": {
    title: "WebSocketBus",
    desc: "A high-performance WebSocket broadcaster that aggregates data from all backend modules and pushes a unified snapshot to the dashboard every second.",
    config: "Max Queue Size: 512 events"
  },
  "WebSocket Device Server": {
    title: "WebSocket Device Server",
    desc: "Handles incoming WebSockets from the ESP8266 Wi-Fi Gateway. Bridges wireless serial streams directly into the python processing pipeline.",
    config: "Endpoint: /ws/device"
  },
  "Frame Parser & Validator": {
    title: "Frame Parser & Validator",
    desc: "Decodes incoming character arrays from the serial stream, validating JSON formats or extracting binary packets using CRC-16 (CCITT-FALSE).",
    config: "Buffer Limit: 256 bytes"
  },
  "Sensor Processor": {
    title: "Sensor Processor",
    desc: "Performs real-time feature extraction on incoming sensor measurements. Tracks running statistical indicators like mean, variance, and delta updates.",
    config: "Rolling Window size (N): 10 frames"
  },
  "Inference Pipeline": {
    title: "Inference Pipeline",
    desc: "Directs incoming feature frames through local neural network classifiers. Predicts presence and flags structural anomalies in the environment.",
    config: "ONNX Inference Engine fallback enabled"
  },
  "Policy Engine": {
    title: "Policy Engine",
    desc: "Combines machine learning anomaly scores with user-defined overrides (rules) to make final device decisions (e.g. flashing warning LEDs).",
    config: "Anomaly Score Threshold (θ): 0.725"
  },
  "Model Manager": {
    title: "Model Manager",
    desc: "Coordinates local ONNX model file updates. Handles loading, verification, and runtime memory allocation for the NPU execution provider.",
    config: "Model Path: backend/aeon/models/"
  },
  "QNN Runtime Manager": {
    title: "QNN Runtime Manager",
    desc: "Initializes the Qualcomm QNN SDK. Directs deep learning computational graphs into Hexagon Tensor Processor hardware blocks.",
    config: "NPU Acceleration: Snapdragon X Elite"
  },
  "Execution Provider": {
    title: "Execution Provider",
    desc: "Controls hardware execution path. Optimizes performance on Snapdragon HTP NPU and falls back to CPU if dependencies are missing.",
    config: "Current Provider: QNN_HTP / CPU"
  },
  "SelfGraph": {
    title: "SelfGraph",
    desc: "An on-device NetworkX knowledge graph mapping relationships between user preferences, room status, comfort levels, and privacy rules.",
    config: "Database file: SQLite memory table"
  },
  "SQLite / FS": {
    title: "SQLite / FS (Event Store)",
    desc: "A power-safe relational database engine using Write-Ahead Logging (WAL) to store historical records, audit logs, and capability tokens.",
    config: "PRAGMA journal_mode = WAL"
  },
  "Metrics & Stats": {
    title: "Metrics & Stats",
    desc: "Exposes real-time CPU, NPU, memory utilization, and power consumption stats to the dashboard and exports them for Prometheus metrics parsing.",
    config: "Metrics Port: 8000/metrics"
  },
  "Sarvam Bridge": {
    title: "Sarvam AI Voice Bridge",
    desc: "Integrates speech-to-text (STT) and text-to-speech (TTS) functionalities, allowing offline voice-activated controls in regional Indian languages.",
    config: "Supported Languages: Hindi, Tamil, English"
  },
  "Privacy & Audit": {
    title: "Privacy & Audit",
    desc: "Monitors outbound traffic to guarantee that 0 KB of raw data leaves the LAN. Computes cryptographically verifiable proofs for access tokens.",
    config: "DPDP Act 2023 Compliant"
  },
  "Migration Service": {
    title: "Migration Service",
    desc: "Signs and packages user identity graphs into encrypted, transferrable ZIP bundles that migrate peer-to-peer using signed QR exchanges.",
    config: "Format: Encrypted AES-256 bundle"
  }
};

export function SoftwareStackPanel({ systemMetrics }: { systemMetrics?: SystemMetrics | null }) {
  const { telemetry, isConnected } = useAeon();
  const [activeNode, setActiveNode] = useState<string | null>(null);

  const serial = telemetry.serialStatus;
  const snapdragon = telemetry.snapdragonStatus;
  const learning = telemetry.continuousLearning;
  const privacy = telemetry.privacyMesh;
  const voice = telemetry.voiceAssistant;
  const graphData = telemetry.knowledgeGraph;

  return (
    <Reveal>
      <div
        className="glass-card overflow-hidden rounded-2xl p-6"
        style={{ borderTop: "3px solid var(--aeon-purple)" }}
      >
        <div className="mb-6 flex items-center gap-3">
          <span
            className="grid h-9 w-9 place-items-center rounded-xl"
            style={{ background: "color-mix(in oklab, var(--aeon-purple) 15%, white)" }}
          >
            <Layers className="h-5 w-5" style={{ color: "var(--aeon-purple)" }} />
          </span>
          <div>
            <h2 className="text-base font-semibold">Software Architecture</h2>
            <p className="text-xs text-muted-foreground">Full-stack layer breakdown — Frontend ↔ Backend</p>
          </div>
        </div>

        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-stretch">
            {/* Frontend Column */}
            <div className="md:col-span-3">
              <StackColumn title="Frontend (Next.js PWA)" tint="var(--aeon-purple)">
                <StackNode
                  name="React UI Components"
                  sublabel="Glassmorphic design"
                  status={isConnected ? "online" : "offline"}
                  onClick={() => setActiveNode("React UI Components")}
                />
                <StackNode
                  name="Live Charts & Widgets"
                  sublabel="Recharts telemetry"
                  status={isConnected ? "online" : "offline"}
                  onClick={() => setActiveNode("Live Charts & Widgets")}
                />
                <StackNode
                  name="WebSocket Client"
                  sublabel="/ws/dashboard"
                  status={isConnected ? "online" : "offline"}
                  metric={isConnected ? "Active" : "Offline"}
                  onClick={() => setActiveNode("WebSocket Client")}
                />
                <StackNode
                  name="REST API Client"
                  sublabel="Fetch wrapper"
                  status={isConnected ? "online" : "offline"}
                  onClick={() => setActiveNode("REST API Client")}
                />
                <StackNode
                  name="Service Worker (PWA)"
                  sublabel="sw.js cache & sync"
                  status={isConnected ? "online" : "idle"}
                  metric="Registered"
                  onClick={() => setActiveNode("Service Worker (PWA)")}
                />
              </StackColumn>
            </div>

            {/* Flow Arrow */}
            <div className="hidden md:flex md:col-span-1 items-center justify-center">
              <FlowArrow />
            </div>

            {/* Backend Columns */}
            <div className="md:col-span-8 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <StackColumn title="API Layer" tint="var(--aeon-blue)">
                <StackNode
                  name="FastAPI Routers"
                  sublabel="/health, /api/*"
                  status={isConnected ? "online" : "offline"}
                  onClick={() => setActiveNode("FastAPI Routers")}
                />
                <StackNode
                  name="WebSocketBus"
                  sublabel="1 Hz Ticker"
                  status={isConnected ? "online" : "offline"}
                  onClick={() => setActiveNode("WebSocketBus")}
                />
              </StackColumn>

              <StackColumn title="Device Gateway" tint="oklch(0.7 0.15 150)">
                <StackNode
                  name="WebSocket Device"
                  sublabel="/ws/device"
                  status={serial.connected ? "online" : "offline"}
                  onClick={() => setActiveNode("WebSocket Device Server")}
                />
                <StackNode
                  name="Frame Parser"
                  sublabel="JSON/Binary Parser"
                  status={serial.connected ? "online" : "offline"}
                  metric={serial.connected ? `${serial.frameRate} F/s` : undefined}
                  onClick={() => setActiveNode("Frame Parser & Validator")}
                />
              </StackColumn>

              <StackColumn title="Pipeline" tint="oklch(0.75 0.15 60)">
                <StackNode
                  name="Sensor Processor"
                  sublabel="Feature Ext"
                  status={serial.connected ? "online" : "offline"}
                  onClick={() => setActiveNode("Sensor Processor")}
                />
                <StackNode
                  name="Inference Pipeline"
                  sublabel="QNN / ONNX run"
                  status={snapdragon.connected ? "online" : "offline"}
                  onClick={() => setActiveNode("Inference Pipeline")}
                />
                <StackNode
                  name="Policy Engine"
                  sublabel="Decision Logic"
                  status={snapdragon.connected ? "online" : "offline"}
                  onClick={() => setActiveNode("Policy Engine")}
                />
              </StackColumn>

              <StackColumn title="AI & Models" tint="var(--aeon-pink)">
                <StackNode
                  name="Model Manager"
                  sublabel="ONNX model loader"
                  status={snapdragon.connected ? "online" : "offline"}
                  onClick={() => setActiveNode("Model Manager")}
                />
                <StackNode
                  name="QNN Runtime"
                  sublabel="Hexagon NPU SDK"
                  status={snapdragon.npuActive ? "online" : "idle"}
                  onClick={() => setActiveNode("QNN Runtime Manager")}
                />
                <StackNode
                  name="Exec Provider"
                  sublabel={snapdragon.executionProvider}
                  status={snapdragon.connected ? "online" : "offline"}
                  onClick={() => setActiveNode("Execution Provider")}
                />
              </StackColumn>

              <StackColumn title="Memory & Graph" tint="oklch(0.72 0.14 160)">
                <StackNode
                  name="SelfGraph"
                  sublabel="NetworkX graph"
                  status={snapdragon.connected ? "online" : "offline"}
                  metric={isConnected ? `${graphData.nodesCount} nodes` : undefined}
                  onClick={() => setActiveNode("SelfGraph")}
                />
                <StackNode
                  name="SQLite / FS"
                  sublabel="WAL Event Store"
                  status={snapdragon.connected ? "online" : "offline"}
                  onClick={() => setActiveNode("SQLite / FS")}
                />
                <StackNode
                  name="Metrics & Stats"
                  sublabel="Time Series stats"
                  status={snapdragon.connected ? "online" : "offline"}
                  metric={systemMetrics ? `CPU ${systemMetrics.cpu_pct.toFixed(0)}%` : undefined}
                  onClick={() => setActiveNode("Metrics & Stats")}
                />
              </StackColumn>

              <StackColumn title="Integrations" tint="oklch(0.7 0.16 260)">
                <StackNode
                  name="Sarvam Bridge"
                  sublabel="STT / TTS Voice"
                  status={voice.sarvamConnected ? "online" : "offline"}
                  onClick={() => setActiveNode("Sarvam Bridge")}
                />
                <StackNode
                  name="Privacy & Audit"
                  sublabel="0 KB Proof"
                  status={snapdragon.connected ? "online" : "offline"}
                  onClick={() => setActiveNode("Privacy & Audit")}
                />
                <StackNode
                  name="Migration"
                  sublabel="P2P export"
                  status={snapdragon.connected ? "online" : "offline"}
                  onClick={() => setActiveNode("Migration Service")}
                />
              </StackColumn>
            </div>
          </div>

          {/* System Services Bar */}
          <div className="border-t border-foreground/8 pt-4">
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              System Services
            </p>
            <SystemServicesBar />
          </div>

          {/* Details Drawer */}
          {activeNode && NODE_DETAILS[activeNode] && (
            <div className="rounded-xl border border-purple-500/20 bg-purple-500/5 p-4 animate-in slide-in-from-bottom duration-200">
              <div className="flex justify-between items-center mb-1.5">
                <h4 className="text-sm font-semibold text-purple-600 dark:text-purple-400">
                  {NODE_DETAILS[activeNode].title}
                </h4>
                <button
                  onClick={() => setActiveNode(null)}
                  className="text-xs text-muted-foreground hover:text-foreground"
                >
                  Close
                </button>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {NODE_DETAILS[activeNode].desc}
              </p>
              {NODE_DETAILS[activeNode].config && (
                <div className="mt-2 text-[10px] font-mono text-purple-500 bg-purple-500/10 px-2 py-0.5 rounded inline-block">
                  {NODE_DETAILS[activeNode].config}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </Reveal>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   PinRow — single row in a board's pin table
───────────────────────────────────────────────────────────────────────────── */
interface PinRowProps {
  pin: string;
  signal: string;
  value?: string;
  status?: "normal" | "warning" | "error";
}

function PinRow({ pin, signal, value, status = "normal" }: PinRowProps) {
  // Use exact oklch colour tokens from design spec:
  //   green  = oklch(0.7 0.15 150)  — normal / healthy
  //   amber  = oklch(0.75 0.15 60)  — warning / idle
  //   red    = oklch(0.65 0.22 27)  — error / offline
  const badgeColor =
    status === "error"
      ? "oklch(0.65 0.22 27)"
      : status === "warning"
        ? "oklch(0.75 0.15 60)"
        : "oklch(0.7 0.15 150)";

  const badgeStyle: React.CSSProperties = {
    color: badgeColor,
    background: `color-mix(in oklab, ${badgeColor} 15%, transparent)`,
    borderColor: `color-mix(in oklab, ${badgeColor} 40%, transparent)`,
  };

  return (
    <tr className="group border-b border-foreground/5 last:border-0">
      {/* Pin badge */}
      <td className="py-2 pr-3 align-top md:align-middle">
        <span className="inline-block rounded-md border border-foreground/10 bg-foreground/[0.07] px-2 py-0.5 font-mono text-xs text-foreground/80">
          {pin}
        </span>
      </td>
      {/* Signal name */}
      <td className="py-2 pr-3 align-top text-sm text-muted-foreground md:align-middle">
        {signal}
      </td>
      {/* Value badge — colour-coded with design-spec oklch tokens */}
      <td className="py-2 align-top md:align-middle">
        <span
          className="inline-block rounded-md border px-2 py-0.5 font-mono text-xs"
          style={badgeStyle}
        >
          {value ?? "—"}
        </span>
      </td>
    </tr>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   BoardCard — chip header + pin table for one microcontroller
───────────────────────────────────────────────────────────────────────────── */
interface BoardCardPin {
  pin: string;
  signal: string;
  value?: string;
  status?: "normal" | "warning" | "error";
}

interface BoardCardProps {
  boardName: string;
  chipName: string;
  connected: boolean;
  lastSeen?: string;
  tint: string;
  pins: BoardCardPin[];
}

function BoardCard({ boardName, chipName, connected, lastSeen, tint, pins }: BoardCardProps) {
  return (
    <div
      className="flex-1 min-w-0 rounded-xl border border-foreground/8 bg-foreground/[0.03] overflow-hidden"
      style={{ borderTop: `2px solid ${tint}` }}
    >
      {/* Chip header */}
      <div className="flex flex-wrap items-center gap-2 px-4 py-3 border-b border-foreground/8">
        <span
          className="grid h-8 w-8 shrink-0 place-items-center rounded-lg"
          style={{ background: `color-mix(in oklab, ${tint} 18%, transparent)` }}
        >
          <Cpu className="h-4 w-4" style={{ color: tint }} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold leading-tight">{boardName}</p>
          <p className="font-mono text-xs text-muted-foreground">{chipName}</p>
        </div>
        {/* Online/offline pill */}
        {connected ? (
          <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-2.5 py-1 text-xs font-medium text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Online
          </span>
        ) : (
          <span className="flex items-center gap-1.5 rounded-full bg-red-500/15 px-2.5 py-1 text-xs font-medium text-red-400">
            <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
            Offline
          </span>
        )}
      </div>

      {/* Disconnected banner */}
      {!connected && (
        <div className="flex items-center gap-2 border-b border-amber-400/20 bg-amber-400/8 px-4 py-2 text-xs font-medium text-amber-400">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          <span>
            Disconnected{lastSeen ? ` · Last seen ${lastSeen}` : ""}
          </span>
        </div>
      )}

      {/* Pin table */}
      <div className="overflow-x-auto px-4 py-2">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-foreground/8">
              <th className="pb-1.5 pr-3 text-xs font-medium text-muted-foreground/60 uppercase tracking-wide">Pin</th>
              <th className="pb-1.5 pr-3 text-xs font-medium text-muted-foreground/60 uppercase tracking-wide">Signal</th>
              <th className="pb-1.5 text-xs font-medium text-muted-foreground/60 uppercase tracking-wide">Value</th>
            </tr>
          </thead>
          <tbody>
            {pins.map((p) => (
              <PinRow key={p.pin} pin={p.pin} signal={p.signal} value={p.value} status={p.status} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   WiringNote — static "all GNDs must be common" amber banner
───────────────────────────────────────────────────────────────────────────── */
function WiringNote() {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-amber-400/30 bg-amber-400/8 px-4 py-2.5 text-sm font-medium text-amber-400">
      <AlertTriangle className="h-4 w-4 shrink-0" />
      <span>⚠ All GNDs must be common (Arduino GND ↔ ESP8266 GND)</span>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Panel 2 — HardwareConnectionPanel
   Diagram 2: Hardware Connection
───────────────────────────────────────────────────────────────────────────── */
export function HardwareConnectionPanel() {
  const { telemetry } = useAeon();
  const serial = telemetry.serialStatus;

  const arduinoPins: BoardCardPin[] = [
    { pin: "D2", signal: "DHT11 Data (Temp/Hum)", value: serial.connected ? `${serial.temperature} °C / ${serial.humidity}%` : "—", status: serial.connected ? "normal" : "error" },
    { pin: "D3", signal: "HC-SR501 PIR (Motion OUT)", value: serial.connected ? serial.motionState : "—", status: serial.connected ? "normal" : "error" },
    { pin: "D4", signal: "Push Button (False Alarm)", value: serial.connected ? "PULLUP (Active)" : "—", status: serial.connected ? "normal" : "error" },
    { pin: "D5", signal: "Status LED", value: serial.connected ? "Active" : "—", status: serial.connected ? "normal" : "error" },
    { pin: "D6", signal: "L298N ENA (PWM Speed)", value: serial.connected ? `${serial.fanSpeedPercent ?? 0}%` : "—", status: serial.connected ? "normal" : "error" },
    { pin: "D7", signal: "L298N IN1 (Direction)", value: serial.connected ? "HIGH" : "—", status: serial.connected ? "normal" : "error" },
    { pin: "D8", signal: "L298N IN2 (Direction)", value: serial.connected ? "LOW" : "—", status: serial.connected ? "normal" : "error" },
    { pin: "D9", signal: "Piezo Buzzer", value: serial.connected ? "Active" : "—", status: serial.connected ? "normal" : "error" },
    { pin: "D10", signal: "RX (from ESP8266 TX)", value: serial.connected ? "9600 bps" : "—", status: serial.connected ? "normal" : "error" },
    { pin: "D11", signal: "TX (to ESP8266 RX)", value: serial.connected ? "9600 bps" : "—", status: serial.connected ? "normal" : "error" },
  ];

  const espPins: BoardCardPin[] = [
    { pin: "D5 (GPIO14)", signal: "RX (from Arduino TX)", value: serial.connected ? "Active" : "—", status: serial.connected ? "normal" : "error" },
    { pin: "D6 (GPIO12)", signal: "TX (to Arduino RX)", value: serial.connected ? "Active" : "—", status: serial.connected ? "normal" : "error" },
  ];

  return (
    <Reveal delay={80}>
      <div
        className="glass-card overflow-hidden rounded-2xl p-6"
        style={{ borderTop: "3px solid var(--aeon-blue)" }}
      >
        <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span
              className="grid h-9 w-9 place-items-center rounded-xl"
              style={{ background: "color-mix(in oklab, var(--aeon-blue) 15%, white)" }}
            >
              <Cpu className="h-5 w-5" style={{ color: "var(--aeon-blue)" }} />
            </span>
            <div>
              <h2 className="text-base font-semibold">Hardware Connections</h2>
              <p className="text-xs text-muted-foreground">Arduino Uno (Atmega328P) &amp; ESP8266 NodeMCU pin map</p>
            </div>
          </div>
          <WiringNote />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
          <BoardCard
            boardName="ARDUINO UNO"
            chipName="ATmega328P"
            connected={serial.connected}
            lastSeen={serial.lastCheckpointSec ? `${serial.lastCheckpointSec}s ago` : undefined}
            tint="var(--aeon-blue)"
            pins={arduinoPins}
          />
          <BoardCard
            boardName="ESP8266 NodeMCU"
            chipName="ESP8266 NodeMCU"
            connected={serial.connected}
            lastSeen={serial.lastCheckpointSec ? `${serial.lastCheckpointSec}s ago` : undefined}
            tint="oklch(0.7 0.15 150)"
            pins={espPins}
          />
        </div>
      </div>
    </Reveal>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   PipelineStage — single stage in the real-time data pipeline
───────────────────────────────────────────────────────────────────────────── */
interface PipelineStageProps {
  step: number;
  icon: React.ElementType;
  label: string;
  sublabel: string;
  status: "online" | "idle" | "offline";
  metric?: string;
  tint: string;
  dimmed?: boolean;
}

function PipelineStage({ step, icon: Icon, label, sublabel, status, metric, tint, dimmed }: PipelineStageProps) {
  const statusChip = {
    online: "bg-emerald-500/15 text-emerald-500 ring-emerald-500/30",
    idle: "bg-amber-400/15 text-amber-400 ring-amber-400/30",
    offline: "bg-red-500/15 text-red-500 ring-red-500/30",
  }[status];

  const statusDot = {
    online: "bg-emerald-500 animate-pulse",
    idle: "bg-amber-400",
    offline: "bg-red-500",
  }[status];

  const statusLabel = { online: "Online", idle: "Idle", offline: "Offline" }[status];

  return (
    <div
      className="flex flex-col items-center gap-2 transition-opacity duration-300"
      style={{ opacity: dimmed ? 0.4 : 1 }}
    >
      {/* Step number chip */}
      <span
        className="inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold text-white"
        style={{ background: tint }}
      >
        {step}
      </span>

      {/* Icon badge */}
      <span
        className="grid h-10 w-10 place-items-center rounded-xl"
        style={{ background: `color-mix(in oklab, ${tint} 18%, transparent)` }}
      >
        <Icon className="h-5 w-5" style={{ color: tint }} />
      </span>

      {/* Label + sublabel */}
      <div className="text-center">
        <p className="text-xs font-semibold leading-tight">{label}</p>
        <p className="mt-0.5 text-[10px] leading-tight text-muted-foreground">{sublabel}</p>
      </div>

      {/* Status chip */}
      <span
        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ring-1 ${statusChip}`}
      >
        <span className={`h-1.5 w-1.5 rounded-full ${statusDot}`} />
        {statusLabel}
      </span>

      {/* Optional metric badge */}
      {metric && (
        <span className="rounded-full border border-foreground/10 bg-foreground/5 px-2 py-0.5 text-[10px] font-medium text-foreground/70">
          {metric}
        </span>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   PipelineArrow — animated SVG arrow between pipeline stages
───────────────────────────────────────────────────────────────────────────── */
interface PipelineArrowProps {
  active: boolean;
}

function PipelineArrow({ active }: PipelineArrowProps) {
  const { ref, inView } = useInView<any>();

  return (
    <svg
      ref={ref}
      width={48}
      height={24}
      viewBox="0 0 48 24"
      fill="none"
      className="shrink-0"
      aria-hidden="true"
    >
      <style>{`
        @keyframes pipeline-draw {
          from { stroke-dashoffset: 52; }
          to   { stroke-dashoffset: 0; }
        }
        .pipeline-line {
          stroke-dasharray: 52;
          stroke-dashoffset: ${inView ? 0 : 52};
          animation: ${inView ? "pipeline-draw 0.6s ease-out forwards" : "none"};
        }
      `}</style>

      {/* Shaft */}
      <line
        className="pipeline-line"
        x1="2"
        y1="12"
        x2="40"
        y2="12"
        stroke={active ? "oklch(0.7 0.15 150)" : "oklch(0.75 0.15 60)"}
        strokeWidth={active ? 2 : 1.5}
        strokeDasharray={active ? undefined : "4 3"}
        strokeLinecap="round"
      />

      {/* Arrowhead */}
      <polyline
        points="34,6 44,12 34,18"
        stroke={active ? "oklch(0.7 0.15 150)" : "oklch(0.75 0.15 60)"}
        strokeWidth={active ? 2 : 1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
        style={{
          opacity: inView ? 1 : 0,
          transition: "opacity 0.3s ease 0.5s",
        }}
      />
    </svg>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   LatencyBanner — end-to-end latency pill
───────────────────────────────────────────────────────────────────────────── */
function LatencyBanner() {
  return (
    <div className="flex justify-center">
      <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-4 py-1.5 text-xs font-medium text-emerald-600 ring-1 ring-emerald-500/30 dark:text-emerald-400">
        ⚡ End-to-End Latency: &lt; 100 ms (Typical)
      </span>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Panel 3 — DataPipelinePanel
   Diagram 3: Real-Time Edge AI Pipeline
───────────────────────────────────────────────────────────────────────────── */
export function DataPipelinePanel() {
  const { telemetry, isConnected } = useAeon();
  const serial = telemetry.serialStatus;
  const snapdragon = telemetry.snapdragonStatus;

  const eventCount = telemetry.events ? telemetry.events.length : 0;

  const stages = [
    {
      step: 1,
      icon: Thermometer,
      label: "Sensor Reading",
      sublabel: "Arduino Uno",
      status: serial.connected ? ("online" as const) : ("offline" as const),
      metric: serial.connected ? `${serial.temperature} °C` : undefined,
      tint: "var(--aeon-purple)",
      dimmed: !serial.connected,
    },
    {
      step: 2,
      icon: Radio,
      label: "Wireless Gateway",
      sublabel: "ESP8266 Wi-Fi",
      status: serial.connected ? ("online" as const) : ("offline" as const),
      metric: serial.connected ? `${serial.baud} bps` : undefined,
      tint: "var(--aeon-blue)",
      dimmed: !serial.connected,
    },
    {
      step: 3,
      icon: Database,
      label: "Backend Ingestion",
      sublabel: "FastAPI /ws/device",
      status: isConnected ? ("online" as const) : ("offline" as const),
      metric: isConnected ? "Port 8000" : undefined,
      tint: "oklch(0.7 0.15 150)",
      dimmed: !isConnected,
    },
    {
      step: 4,
      icon: Cpu,
      label: "Feature Extraction",
      sublabel: "Rolling Stats (N=10)",
      status: snapdragon.connected ? ("online" as const) : ("offline" as const),
      metric: snapdragon.connected ? `CPU ${snapdragon.cpuPct.toFixed(0)}%` : undefined,
      tint: "oklch(0.75 0.15 60)",
      dimmed: !snapdragon.connected,
    },
    {
      step: 5,
      icon: BrainCircuit,
      label: "AI Inference",
      sublabel: "sentinel_anomaly.onnx",
      status: snapdragon.connected ? ("online" as const) : ("offline" as const),
      metric: snapdragon.connected ? snapdragon.modelName.substring(0, 15) : undefined,
      tint: "var(--aeon-pink)",
      dimmed: !snapdragon.connected,
    },
    {
      step: 6,
      icon: Zap,
      label: "Hexagon NPU",
      sublabel: snapdragon.executionProvider,
      status: snapdragon.npuActive ? ("online" as const) : ("idle" as const),
      metric: snapdragon.connected ? `${snapdragon.latencyMs.toFixed(1)} ms` : undefined,
      tint: "oklch(0.72 0.14 160)",
      dimmed: !snapdragon.connected,
    },
    {
      step: 7,
      icon: Layers,
      label: "Broadcast to UI",
      sublabel: "WebSocket Ticker",
      status: isConnected ? ("online" as const) : ("offline" as const),
      metric: isConnected ? `${eventCount} events` : undefined,
      tint: "oklch(0.7 0.16 260)",
      dimmed: !isConnected,
    },
  ];

  return (
    <Reveal delay={160}>
      <div
        className="glass-card overflow-hidden rounded-2xl p-6"
        style={{ borderTop: "3px solid oklch(0.7 0.15 150)" }}
      >
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span
              className="grid h-9 w-9 place-items-center rounded-xl"
              style={{ background: "color-mix(in oklab, oklch(0.7 0.15 150) 15%, white)" }}
            >
              <GitBranch className="h-5 w-5" style={{ color: "oklch(0.7 0.15 150)" }} />
            </span>
            <div>
              <h2 className="text-base font-semibold">Real-Time Data Pipeline</h2>
              <p className="text-xs text-muted-foreground">Sensor → Gateway → Inference → Policy → UI</p>
            </div>
          </div>
          <LatencyBanner />
        </div>

        {/* Desktop horizontal pipeline view */}
        <div className="hidden md:flex items-center justify-between gap-2 overflow-x-auto py-4">
          {stages.map((stage, idx) => (
            <Fragment key={stage.step}>
              <PipelineStage
                step={stage.step}
                icon={stage.icon}
                label={stage.label}
                sublabel={stage.sublabel}
                status={stage.status}
                metric={stage.metric}
                tint={stage.tint}
                dimmed={stage.dimmed}
              />
              {idx < stages.length - 1 && (
                <PipelineArrow active={stages[idx].status === "online" && stages[idx + 1].status === "online"} />
              )}
            </Fragment>
          ))}
        </div>

        {/* Mobile vertical stepper view */}
        <div className="flex flex-col gap-4 md:hidden">
          {stages.map((stage) => (
            <div key={stage.step} className="flex items-center gap-3 border-b border-foreground/5 last:border-0 pb-3 last:pb-0">
              <span
                className="grid h-8 w-8 place-items-center rounded-lg shrink-0"
                style={{ background: `color-mix(in oklab, ${stage.tint} 15%, transparent)`, color: stage.tint }}
              >
                <stage.icon className="h-4 w-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold leading-tight">{stage.label}</p>
                <p className="text-[10px] text-muted-foreground">{stage.sublabel}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {stage.metric && (
                  <span className="rounded bg-foreground/5 px-1.5 py-0.5 text-[10px] font-medium text-foreground/70">
                    {stage.metric}
                  </span>
                )}
                <span className={`h-2 w-2 rounded-full ${stage.status === "online" ? "bg-emerald-500 animate-pulse" : stage.status === "idle" ? "bg-amber-400" : "bg-red-500"}`} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </Reveal>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   LearningStep — one step in the bidirectional learning stepper
───────────────────────────────────────────────────────────────────────────── */
interface LearningStepProps {
  step: number;
  label: string;
  bullets: string[];
  badge?: string;
  tint: string;
  active?: boolean;
}

function LearningStep({ step, label, bullets, badge, tint, active = false }: LearningStepProps) {
  return (
    <div className="flex min-w-0 flex-1 flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        {/* Numbered circle */}
        <div className="flex items-center gap-2">
          <span
            className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-sm font-semibold transition-colors"
            style={
              active
                ? { background: tint, color: "#fff" }
                : { background: "color-mix(in oklab, " + tint + " 18%, transparent)", color: tint }
            }
          >
            {step}
          </span>
          <span
            className="text-sm font-semibold leading-tight"
            style={active ? { color: tint } : undefined}
          >
            {label}
          </span>
        </div>
        {/* Live value badge */}
        {badge && (
          <span
            className="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium"
            style={{
              background: "color-mix(in oklab, " + tint + " 15%, transparent)",
              color: tint,
              border: "1px solid color-mix(in oklab, " + tint + " 35%, transparent)",
            }}
          >
            {badge}
          </span>
        )}
      </div>
      {/* Bullet list */}
      <ul className="ml-10 space-y-0.5">
        {bullets.map((bullet, i) => (
          <li key={i} className="text-xs text-muted-foreground">
            {bullet}
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   StepConnector — horizontal (desktop) / vertical (mobile) dashed animated line
───────────────────────────────────────────────────────────────────────────── */
interface StepConnectorProps {
  active?: boolean;
}

function StepConnector({ active = false }: StepConnectorProps) {
  const { ref: hRef, inView: hInView } = useInView<any>();
  const { ref: vRef, inView: vInView } = useInView<any>();

  const stroke = active
    ? "var(--aeon-purple)"
    : "color-mix(in oklab, var(--foreground) 28%, transparent)";
  const strokeWidth = active ? 2 : 1.5;

  return (
    <>
      {/* Vertical connector — visible on mobile only */}
      <div className="mx-4 my-1 flex justify-center md:hidden">
        <svg
          ref={vRef}
          width={16}
          height={28}
          viewBox="0 0 16 28"
          fill="none"
          aria-hidden="true"
        >
          <style>{`
            @keyframes step-draw-v {
              from { stroke-dashoffset: 28; }
              to   { stroke-dashoffset: 0; }
            }
            .step-line-v {
              stroke-dasharray: 4 3;
              stroke-dashoffset: ${vInView ? 0 : 28};
              animation: ${vInView ? "step-draw-v 0.5s ease-out forwards" : "none"};
            }
          `}</style>
          <line
            className="step-line-v"
            x1="8" y1="2" x2="8" y2="26"
            stroke={stroke}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
        </svg>
      </div>

      {/* Horizontal connector — visible on desktop only */}
      <div className="hidden flex-1 items-center md:flex" style={{ minWidth: 0 }}>
        <svg
          ref={hRef}
          width="100%"
          height={16}
          preserveAspectRatio="none"
          viewBox="0 0 64 16"
          fill="none"
          aria-hidden="true"
          style={{ display: "block", width: "100%", minWidth: 16 }}
        >
          <style>{`
            @keyframes step-draw-h {
              from { stroke-dashoffset: 64; }
              to   { stroke-dashoffset: 0; }
            }
            .step-line-h {
              stroke-dasharray: 4 3;
              stroke-dashoffset: ${hInView ? 0 : 64};
              animation: ${hInView ? "step-draw-h 0.6s ease-out forwards" : "none"};
            }
          `}</style>
          <line
            className="step-line-h"
            x1="2" y1="8" x2="62" y2="8"
            stroke={stroke}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
        </svg>
      </div>
    </>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   PersistenceBanner — green pill confirming EEPROM persistence
───────────────────────────────────────────────────────────────────────────── */
interface PersistenceBannerProps {
  fresh: boolean;
}

function PersistenceBanner({ fresh }: PersistenceBannerProps) {
  return (
    <div
      className="flex w-full items-center justify-center gap-2 rounded-full px-4 py-2 text-sm font-medium"
      style={{
        background: "color-mix(in oklab, oklch(0.7 0.15 150) 12%, transparent)",
        border: "1px solid color-mix(in oklab, oklch(0.7 0.15 150) 30%, transparent)",
      }}
    >
      <HardDrive
        className="h-4 w-4 shrink-0"
        style={{ color: "oklch(0.7 0.15 150)" }}
      />
      {fresh ? (
        <CheckCircle2
          className="h-4 w-4 shrink-0 animate-pulse"
          style={{ color: "oklch(0.7 0.15 150)" }}
        />
      ) : (
        <CheckCircle2
          className="h-4 w-4 shrink-0 opacity-40"
          style={{ color: "oklch(0.7 0.15 150)" }}
        />
      )}
      <span style={{ color: "oklch(0.7 0.15 150)" }}>
        ✓ Confirmed &amp; Persisted Across Power Cycles
      </span>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Panel 4 — LearningFlowPanel
   Diagram 4: Bidirectional Learning
───────────────────────────────────────────────────────────────────────────── */
export function LearningFlowPanel({ learningStatus }: { learningStatus?: LearningStatus | null }) {
  const { telemetry } = useAeon();
  const learning = telemetry.continuousLearning;
  const serial = telemetry.serialStatus;

  const isRecent = serial.connected && serial.lastCheckpointSec < 60;

  return (
    <Reveal delay={240}>
      <div
        className="glass-card overflow-hidden rounded-2xl p-6"
        style={{ borderTop: "3px solid var(--aeon-pink)" }}
      >
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span
              className="grid h-9 w-9 place-items-center rounded-xl"
              style={{ background: "color-mix(in oklab, var(--aeon-pink) 15%, white)" }}
            >
              <BrainCircuit className="h-5 w-5" style={{ color: "var(--aeon-pink)" }} />
            </span>
            <div>
              <h2 className="text-base font-semibold">Bidirectional Learning Flow</h2>
              <p className="text-xs text-muted-foreground">False alarm → Learning engine → EEPROM checkpoint</p>
            </div>
          </div>
          <div className="w-full sm:w-auto">
            <PersistenceBanner fresh={isRecent} />
          </div>
        </div>

        {/* Desktop Step Stepper */}
        <div className="hidden md:flex items-start justify-between gap-2 py-4">
          <LearningStep
            step={1}
            label="False Alarm Detected"
            bullets={["User button press", "Dashboard dismissal", `Flagged count: ${learning.falseAlarmsFlagged}`]}
            badge={learning.falseAlarmsFlagged > 0 ? "Flagged" : "Waiting"}
            tint="var(--aeon-purple)"
            active={learning.falseAlarmsFlagged > 0}
          />
          <StepConnector active={learning.falseAlarmsFlagged > 0} />
          <LearningStep
            step={2}
            label="Learning Engine"
            bullets={["Sensitivity gradient shift", "Adjust sensitivity (θ)", `Current θ: ${learning.sensitivityThreshold.toFixed(3)}`]}
            badge={learning.status}
            tint="var(--aeon-blue)"
            active={learning.status !== "idle" && learning.status !== "Waiting for backend..."}
          />
          <StepConnector active={learning.progressPct > 0} />
          <LearningStep
            step={3}
            label="Model/Policy Update"
            bullets={[`Training: ${learning.progressPct}%`, "Weights compilation", `Last: ${learningStatus?.last_train ? new Date(learningStatus.last_train).toLocaleTimeString() : "Pending"}`]}
            badge={learning.progressPct === 100 ? "Ready" : `${learning.progressPct}%`}
            tint="var(--aeon-pink)"
            active={learning.progressPct > 0}
          />
          <StepConnector active={serial.connected} />
          <LearningStep
            step={4}
            label="Command Back to MCU"
            bullets={["WebSocket transmission", "Baud rate sync: 9600 bps"]}
            badge={serial.connected ? "Active" : "Offline"}
            tint="oklch(0.7 0.15 150)"
            active={serial.connected}
          />
          <StepConnector active={serial.connected && isRecent} />
          <LearningStep
            step={5}
            label="EEPROM Checkpoint"
            bullets={[`Allocation: ${serial.eepromUsagePct}%`, `Checkpoint: ${serial.lastCheckpointSec}s ago`]}
            badge={isRecent ? "Saved" : "Synced"}
            tint="oklch(0.72 0.14 160)"
            active={serial.connected && isRecent}
          />
        </div>

        {/* Mobile Stepper */}
        <div className="flex flex-col gap-4 md:hidden">
          <LearningStep
            step={1}
            label="False Alarm Detected"
            bullets={["User button press", "Dashboard dismissal", `Flagged count: ${learning.falseAlarmsFlagged}`]}
            badge={learning.falseAlarmsFlagged > 0 ? "Flagged" : "Waiting"}
            tint="var(--aeon-purple)"
            active={learning.falseAlarmsFlagged > 0}
          />
          <StepConnector active={learning.falseAlarmsFlagged > 0} />
          <LearningStep
            step={2}
            label="Learning Engine"
            bullets={["Sensitivity gradient shift", "Adjust sensitivity (θ)", `Current θ: ${learning.sensitivityThreshold.toFixed(3)}`]}
            badge={learning.status}
            tint="var(--aeon-blue)"
            active={learning.status !== "idle" && learning.status !== "Waiting for backend..."}
          />
          <StepConnector active={learning.progressPct > 0} />
          <LearningStep
            step={3}
            label="Model/Policy Update"
            bullets={[`Training: ${learning.progressPct}%`, "Weights compilation", `Last: ${learningStatus?.last_train ? new Date(learningStatus.last_train).toLocaleTimeString() : "Pending"}`]}
            badge={learning.progressPct === 100 ? "Ready" : `${learning.progressPct}%`}
            tint="var(--aeon-pink)"
            active={learning.progressPct > 0}
          />
          <StepConnector active={serial.connected} />
          <LearningStep
            step={4}
            label="Command Back to MCU"
            bullets={["WebSocket transmission", "Baud rate sync: 9600 bps"]}
            badge={serial.connected ? "Active" : "Offline"}
            tint="oklch(0.7 0.15 150)"
            active={serial.connected}
          />
          <StepConnector active={serial.connected && isRecent} />
          <LearningStep
            step={5}
            label="EEPROM Checkpoint"
            bullets={[`Allocation: ${serial.eepromUsagePct}%`, `Checkpoint: ${serial.lastCheckpointSec}s ago`]}
            badge={isRecent ? "Saved" : "Synced"}
            tint="oklch(0.72 0.14 160)"
            active={serial.connected && isRecent}
          />
        </div>
      </div>
    </Reveal>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   TopologyNode — icon badge + name + status dot + optional service list
───────────────────────────────────────────────────────────────────────────── */
interface TopologyNodeProps {
  icon: React.ElementType;
  name: string;
  sublabel?: string;
  status: "online" | "idle" | "offline" | "unknown";
  services?: string[];
  tint: string;
}

export function TopologyNode({ icon: Icon, name, sublabel, status, services, tint }: TopologyNodeProps) {
  const dotClass =
    status === "online"
      ? "bg-emerald-500 animate-pulse"
      : status === "idle"
      ? "bg-amber-400"
      : status === "offline"
      ? "bg-red-500"
      : "bg-gray-300";

  return (
    <div
      className="glass-card flex flex-col gap-2 rounded-xl p-3"
      style={{ borderTop: `2px solid ${tint}` }}
    >
      {/* Icon badge + name row */}
      <div className="flex items-center gap-2">
        <span
          className="grid h-8 w-8 shrink-0 place-items-center rounded-lg"
          style={{ background: `color-mix(in oklab, ${tint} 18%, transparent)` }}
        >
          <Icon className="h-4 w-4" style={{ color: tint }} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-semibold leading-tight text-foreground">{name}</p>
          {sublabel && (
            <p className="truncate text-[10px] leading-tight text-muted-foreground">{sublabel}</p>
          )}
        </div>
        {/* Status dot */}
        <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${dotClass}`} aria-label={status} />
      </div>

      {/* Optional service list */}
      {services && services.length > 0 && (
        <ul className="flex flex-col gap-0.5 border-t border-foreground/8 pt-2">
          {services.map((svc) => (
            <li key={svc} className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
              <span className="h-1 w-1 shrink-0 rounded-full bg-foreground/30" />
              {svc}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   ProtocolLabel — small rounded chip placed on a topology edge
───────────────────────────────────────────────────────────────────────────── */
interface ProtocolLabelProps {
  protocol: string;
}

export function ProtocolLabel({ protocol }: ProtocolLabelProps) {
  return (
    <span className="inline-flex items-center rounded-full border border-foreground/10 bg-background/80 px-2 py-0.5 text-[10px] font-medium text-foreground/70 shadow-sm backdrop-blur-sm">
      {protocol}
    </span>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   TopologyEdge — SVG curved path with animated stroke-dashoffset
───────────────────────────────────────────────────────────────────────────── */
interface TopologyEdgeProps {
  /** Total path length estimate — used for the dasharray/dashoffset animation */
  pathLength?: number;
  /** Whether the edge is healthy (drives colour) */
  active?: boolean;
  /** Protocol chip label rendered at the midpoint */
  protocol?: string;
  /** Horizontal (default) or vertical orientation */
  orientation?: "horizontal" | "vertical";
}

export function TopologyEdge({
  pathLength = 80,
  active = true,
  protocol,
  orientation = "horizontal",
}: TopologyEdgeProps) {
  const { ref, inView } = useInView<any>();

  const strokeColour = active
    ? "var(--aeon-blue)"
    : "oklch(0.75 0.15 60)";

  const animStyle: React.CSSProperties = {
    strokeDasharray: pathLength,
    strokeDashoffset: inView ? 0 : pathLength,
    transition: inView ? "stroke-dashoffset 0.7s ease-out" : "none",
  };

  const isHorizontal = orientation === "horizontal";

  // SVG dimensions and path
  const width = isHorizontal ? 96 : 24;
  const height = isHorizontal ? 24 : 64;
  const path = isHorizontal
    ? `M 4,12 C 28,12 68,12 92,12`     // straight with cubic handles (room for label)
    : `M 12,4 C 12,24 12,40 12,60`;    // vertical straight

  return (
    <div className="relative flex items-center justify-center">
      <svg
        ref={ref}
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        fill="none"
        aria-hidden="true"
        className="shrink-0"
      >
        {/* Main path */}
        <path
          d={path}
          stroke={strokeColour}
          strokeWidth={active ? 2 : 1.5}
          strokeLinecap="round"
          strokeDasharray={active ? undefined : "5 3"}
          style={active ? animStyle : undefined}
          opacity={active ? 1 : 0.5}
        />

        {/* Arrowhead at end */}
        {isHorizontal ? (
          <polyline
            points="84,7 93,12 84,17"
            stroke={strokeColour}
            strokeWidth={active ? 2 : 1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
            style={{ opacity: inView ? 1 : 0, transition: "opacity 0.3s ease 0.6s" }}
          />
        ) : (
          <polyline
            points="7,52 12,61 17,52"
            stroke={strokeColour}
            strokeWidth={active ? 2 : 1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
            style={{ opacity: inView ? 1 : 0, transition: "opacity 0.3s ease 0.6s" }}
          />
        )}
      </svg>

      {/* Protocol chip — floated above midpoint */}
      {protocol && (
        <span className="pointer-events-none absolute">
          <ProtocolLabel protocol={protocol} />
        </span>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Panel 5 — NetworkTopologyPanel
   Diagram 6: Network & Deployment
───────────────────────────────────────────────────────────────────────────── */
export function NetworkTopologyPanel() {
  const { telemetry, isConnected } = useAeon();
  const serial = telemetry.serialStatus;
  const snapdragon = telemetry.snapdragonStatus;
  const voice = telemetry.voiceAssistant;

  return (
    <Reveal delay={320}>
      <div
        className="glass-card overflow-hidden rounded-2xl p-6"
        style={{ borderTop: "3px solid oklch(0.65 0.18 220)" }}
      >
        <div className="mb-6 flex items-center gap-3">
          <span
            className="grid h-9 w-9 place-items-center rounded-xl"
            style={{ background: "color-mix(in oklab, oklch(0.65 0.18 220) 15%, white)" }}
          >
            <Network className="h-5 w-5" style={{ color: "oklch(0.65 0.18 220)" }} />
          </span>
          <div>
            <h2 className="text-base font-semibold">Network Topology</h2>
            <p className="text-xs text-muted-foreground">Internet → Snapdragon PC → Wi-Fi hotspot → Hardware</p>
          </div>
        </div>

        {/* Desktop Layout */}
        <div className="hidden md:grid grid-cols-5 items-center gap-2 py-6">
          {/* Column 1: Internet */}
          <div className="flex justify-center">
            <TopologyNode
              icon={Cloud}
              name="Internet"
              sublabel="Sarvam Speech API"
              status={voice.sarvamConnected ? "online" : "offline"}
              tint="var(--aeon-purple)"
            />
          </div>

          {/* Connection: Internet -> Snapdragon PC */}
          <TopologyEdge active={voice.sarvamConnected} protocol="HTTPS" />

          {/* Column 2: Snapdragon PC & Wi-Fi Hotspot */}
          <div className="flex flex-col gap-8 items-center justify-center">
            <TopologyNode
              icon={Cpu}
              name="Snapdragon PC"
              sublabel="Edge AI Engine"
              status={snapdragon.connected ? "online" : "offline"}
              tint="var(--aeon-blue)"
              services={["FastAPI (8000/8001)", "QNN Runtime & NPU", "SelfGraph", "PWA Dashboard"]}
            />
            <TopologyNode
              icon={Wifi}
              name='Wi-Fi "AEON-EDGE"'
              sublabel="Local Hotspot (2.4 GHz)"
              status={snapdragon.connected ? "online" : "offline"}
              tint="oklch(0.7 0.15 150)"
            />
          </div>

          {/* Connections: PC/Hotspot -> Gateway/Mobile */}
          <div className="flex flex-col gap-12 items-center justify-center">
            <TopologyEdge active={serial.connected} protocol="WebSocket" />
            <TopologyEdge active={isConnected} protocol="WebSocket" />
          </div>

          {/* Column 3: ESP8266 Gateway, Arduino Sentinel, & Mobile Client */}
          <div className="flex flex-col gap-5 items-center justify-center">
            <TopologyNode
              icon={Radio}
              name="ESP8266 Gateway"
              sublabel="Wi-Fi transparent bridge"
              status={serial.connected ? "online" : "offline"}
              tint="oklch(0.75 0.15 60)"
            />
            <div className="flex h-3 w-px items-center justify-center border-l border-dashed border-foreground/30">
              <span className="bg-background px-1 text-[7px] text-muted-foreground uppercase tracking-tight">UART @ 9600</span>
            </div>
            <TopologyNode
              icon={Cpu}
              name="Arduino Sentinel"
              sublabel="Hardware Sensor Hub"
              status={serial.connected ? "online" : "offline"}
              tint="var(--aeon-purple)"
            />
            <TopologyNode
              icon={Smartphone}
              name="Mobile Phone"
              sublabel="PWA Web Dashboard"
              status={isConnected ? "online" : "offline"}
              tint="oklch(0.7 0.16 260)"
            />
          </div>
        </div>

        {/* Mobile vertical list layout */}
        <div className="flex flex-col gap-4 md:hidden">
          <TopologyNode
            icon={Cloud}
            name="Internet"
            sublabel="Sarvam Speech API"
            status={voice.sarvamConnected ? "online" : "offline"}
            tint="var(--aeon-purple)"
          />
          <div className="mx-auto h-6 w-px border-l-2 border-dashed border-foreground/20" />
          <TopologyNode
            icon={Cpu}
            name="Snapdragon PC"
            sublabel="Edge AI Engine"
            status={snapdragon.connected ? "online" : "offline"}
            tint="var(--aeon-blue)"
            services={["FastAPI (8000/8001)", "QNN/NPU", "SelfGraph"]}
          />
          <div className="mx-auto h-6 w-px border-l-2 border-dashed border-foreground/20" />
          <TopologyNode
            icon={Wifi}
            name='Wi-Fi "AEON-EDGE"'
            sublabel="Local Hotspot (2.4 GHz)"
            status={snapdragon.connected ? "online" : "offline"}
            tint="oklch(0.7 0.15 150)"
          />
          <div className="mx-auto h-6 w-px border-l-2 border-dashed border-foreground/20" />
          <div className="grid grid-cols-3 gap-2">
            <TopologyNode
              icon={Radio}
              name="ESP8266"
              sublabel="Wi-Fi Bridge"
              status={serial.connected ? "online" : "offline"}
              tint="oklch(0.75 0.15 60)"
            />
            <TopologyNode
              icon={Cpu}
              name="Arduino"
              sublabel="Sentinel"
              status={serial.connected ? "online" : "offline"}
              tint="var(--aeon-purple)"
            />
            <TopologyNode
              icon={Smartphone}
              name="Mobile Phone"
              sublabel="PWA"
              status={isConnected ? "online" : "offline"}
              tint="oklch(0.7 0.16 260)"
            />
          </div>
        </div>
      </div>
    </Reveal>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   ResilienceStep — circle icon + label + optional θ badge + detail text
───────────────────────────────────────────────────────────────────────────── */
interface ResilienceStepProps {
  /** 1-based step number, used as aria label */
  step: number;
  /** lucide-react icon element type */
  icon: React.ElementType;
  /** Short step label */
  label: string;
  /** Optional θ (model weight) value, e.g. 0.725 */
  theta?: number;
  /** Detail text rendered below the label */
  detail?: string;
  /** Whether this step is the currently active one */
  active?: boolean;
  /** Accent colour override — defaults to `var(--aeon-pink)` */
  tint?: string;
  /** If true the circle and connecting track are rendered in red */
  danger?: boolean;
}

export function ResilienceStep({
  step,
  icon: Icon,
  label,
  theta,
  detail,
  active = false,
  tint = "var(--aeon-pink)",
  danger = false,
}: ResilienceStepProps) {
  const accentColor = danger ? "oklch(0.65 0.22 27)" : tint;

  const circleBg = active
    ? accentColor
    : `color-mix(in oklab, ${accentColor} 20%, transparent)`;

  const circleText = active ? "#fff" : accentColor;

  return (
    <div className="flex flex-col items-center gap-2 min-w-0">
      {/* θ badge — sits above the circle when present */}
      {theta !== undefined ? (
        <span
          className="rounded-full px-2 py-0.5 text-[10px] font-semibold tabular-nums"
          style={{
            background: `color-mix(in oklab, ${accentColor} 18%, transparent)`,
            color: accentColor,
            border: `1px solid color-mix(in oklab, ${accentColor} 35%, transparent)`,
          }}
        >
          θ={theta.toFixed(3)}
        </span>
      ) : (
        /* Invisible placeholder to keep vertical alignment consistent */
        <span className="h-[22px]" aria-hidden="true" />
      )}

      {/* Circle icon */}
      <span
        aria-label={`Step ${step}`}
        className="grid h-10 w-10 shrink-0 place-items-center rounded-full transition-all duration-300"
        style={{
          background: circleBg,
          color: circleText,
          outline: `2px solid color-mix(in oklab, ${accentColor} 40%, transparent)`,
          outlineOffset: active ? "3px" : "0px",
        }}
      >
        <Icon className="h-5 w-5" />
      </span>

      {/* Label */}
      <p
        className="max-w-[80px] text-center text-[11px] font-semibold leading-tight"
        style={active ? { color: accentColor } : undefined}
      >
        {label}
      </p>

      {/* Detail text */}
      {detail && (
        <p className="max-w-[90px] text-center text-[10px] leading-tight text-muted-foreground">
          {detail}
        </p>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   StepTrack — full-width progress rail with gradient fill
   Driven by `activeIndex` (0-based, 0 = first step fully filled)
───────────────────────────────────────────────────────────────────────────── */
interface StepTrackProps {
  /** Total number of steps */
  totalSteps: number;
  /** 0-based index of the currently active step */
  activeIndex: number;
  /** Accent colour for the filled portion — defaults to `var(--aeon-pink)` */
  tint?: string;
}

export function StepTrack({ totalSteps, activeIndex, tint = "var(--aeon-pink)" }: StepTrackProps) {
  const fillPct = totalSteps <= 1 ? 100 : Math.round((activeIndex / (totalSteps - 1)) * 100);

  return (
    <div
      aria-label={`Progress: step ${activeIndex + 1} of ${totalSteps}`}
      role="progressbar"
      aria-valuenow={activeIndex + 1}
      aria-valuemin={1}
      aria-valuemax={totalSteps}
      className="relative h-2 w-full overflow-hidden rounded-full"
      style={{ background: `color-mix(in oklab, ${tint} 15%, transparent)` }}
    >
      {/* Filled gradient portion */}
      <div
        className="absolute inset-y-0 left-0 rounded-full transition-all duration-700 ease-out"
        style={{
          width: `${fillPct}%`,
          background: `linear-gradient(to right, color-mix(in oklab, ${tint} 60%, transparent), ${tint})`,
        }}
      />

      {/* Step markers */}
      {Array.from({ length: totalSteps }).map((_, i) => {
        const leftPct = totalSteps <= 1 ? 0 : (i / (totalSteps - 1)) * 100;
        const passed = i <= activeIndex;
        return (
          <span
            key={i}
            aria-hidden="true"
            className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background transition-all duration-300"
            style={{
              left: `${leftPct}%`,
              background: passed ? tint : `color-mix(in oklab, ${tint} 30%, transparent)`,
            }}
          />
        );
      })}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   BenefitChip — green rounded chip for benefit labels
───────────────────────────────────────────────────────────────────────────── */
interface BenefitChipProps {
  label: string;
}

export function BenefitChip({ label }: BenefitChipProps) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden="true" />
      {label}
    </span>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Panel 6 — PowerResiliencePanel
   Diagram 7: Power Failure Resilience
───────────────────────────────────────────────────────────────────────────── */
export function PowerResiliencePanel() {
  const { telemetry } = useAeon();
  const learning = telemetry.continuousLearning;
  const serial = telemetry.serialStatus;

  let activeIndex = 7;
  if (!serial.connected) {
    activeIndex = 4; // Power OFF
  } else if (learning.progressPct > 0 && learning.progressPct < 100) {
    activeIndex = 2; // Learning & Update
  } else if (learning.falseAlarmsFlagged > 0 && learning.progressPct === 0) {
    activeIndex = 1; // User Feedback
  }

  const benefits = [
    "Survives Power Cuts",
    "Instant Recovery < 200ms",
    "No Loss of Learning",
    "Never Forgets User",
    "Truly Persistent Edge AI",
  ];

  return (
    <Reveal delay={400}>
      <div
        className="glass-card overflow-hidden rounded-2xl p-6"
        style={{ borderTop: "3px solid oklch(0.72 0.17 60)" }}
      >
        <div className="mb-6 flex items-center gap-3">
          <span
            className="grid h-9 w-9 place-items-center rounded-xl"
            style={{ background: "color-mix(in oklab, oklch(0.72 0.17 60) 15%, white)" }}
          >
            <Zap className="h-5 w-5" style={{ color: "oklch(0.72 0.17 60)" }} />
          </span>
          <div>
            <h2 className="text-base font-semibold">Power Failure Resilience</h2>
            <p className="text-xs text-muted-foreground">8-step recovery timeline — Boot &lt; 10ms, restore &lt; 200ms</p>
          </div>
        </div>

        <div className="space-y-6">
          {/* Step Progress Track */}
          <div className="px-4">
            <StepTrack totalSteps={8} activeIndex={activeIndex} tint="oklch(0.72 0.17 60)" />
          </div>

          {/* Steps list (horizontal scroll on mobile) */}
          <div className="flex items-start justify-between gap-4 overflow-x-auto pb-4 pt-2">
            <ResilienceStep
              step={1}
              icon={Cpu}
              label="Normal Operation"
              theta={0.725}
              detail="Model v1 Active"
              active={activeIndex === 0}
              tint="oklch(0.72 0.17 60)"
            />
            <ResilienceStep
              step={2}
              icon={Settings2}
              label="User Feedback"
              detail={`Flagged: ${learning.falseAlarmsFlagged}`}
              active={activeIndex === 1}
              tint="oklch(0.72 0.17 60)"
            />
            <ResilienceStep
              step={3}
              icon={BrainCircuit}
              label="Learning & Update"
              theta={0.675}
              detail={`Progress: ${learning.progressPct}%`}
              active={activeIndex === 2}
              tint="oklch(0.72 0.17 60)"
            />
            <ResilienceStep
              step={4}
              icon={HardDrive}
              label="EEPROM Checkpoint"
              detail={`Usage: ${serial.eepromUsagePct}%`}
              active={activeIndex === 3}
              tint="oklch(0.72 0.17 60)"
            />
            <ResilienceStep
              step={5}
              icon={Zap}
              label="Power OFF"
              detail="Unexpected"
              active={activeIndex === 4}
              danger
              tint="oklch(0.72 0.17 60)"
            />
            <ResilienceStep
              step={6}
              icon={RotateCcw}
              label="Power ON / Boot"
              detail="Instant Restore"
              active={activeIndex === 5}
              tint="oklch(0.72 0.17 60)"
            />
            <ResilienceStep
              step={7}
              icon={ShieldCheck}
              label="CRC Validation"
              detail="Integrity Check"
              active={activeIndex === 6}
              tint="oklch(0.72 0.17 60)"
            />
            <ResilienceStep
              step={8}
              icon={CheckCircle2}
              label="Restored Operation"
              theta={learning.sensitivityThreshold}
              detail="Model v2 Active"
              active={activeIndex === 7}
              tint="oklch(0.72 0.17 60)"
            />
          </div>

          {/* Benefits Chips */}
          <div className="border-t border-foreground/8 pt-4">
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Resilience Capabilities
            </p>
            <div className="flex flex-wrap gap-2">
              {benefits.map((benefit) => (
                <BenefitChip key={benefit} label={benefit} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </Reveal>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   ArchitecturePage — root component
───────────────────────────────────────────────────────────────────────────── */
export function ArchitecturePage() {
  const { isConnected } = useAeon();

  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [learningStatus, setLearningStatus] = useState<LearningStatus | null>(null);

  useEffect(() => {
    fetchMetricsSystem()
      .then(setSystemMetrics)
      .catch(() => {
        /* silently ignore — panel will show stale/empty state */
      });

    fetchLearningStatus()
      .then(setLearningStatus)
      .catch(() => {
        /* silently ignore */
      });
  }, []);

  return (
    <div className="space-y-6 p-4 md:p-6 lg:p-8">
      {/* Stale data warning */}
      {!isConnected && <StaleBanner />}

      {/* Page header */}
      <Reveal>
        <div>
          <h1
            className="text-3xl font-semibold tracking-tight md:text-4xl"
            style={{ fontFamily: "'Instrument Serif', serif", fontWeight: 400 }}
          >
            <span className="text-gradient">System Architecture</span>
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Live visualization of every layer in the ÆON intelligence fabric.
          </p>
        </div>
      </Reveal>

      {/* Six architecture panels */}
      <SoftwareStackPanel systemMetrics={systemMetrics} />
      <HardwareConnectionPanel />
      <DataPipelinePanel />
      <LearningFlowPanel learningStatus={learningStatus} />
      <NetworkTopologyPanel />
      <PowerResiliencePanel />
    </div>
  );
}
