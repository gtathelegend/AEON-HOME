/**
 * ÆON Backend REST API client
 * Base URL: VITE_API_BASE_URL (default: http://localhost:8000)
 */

const BASE = (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_API_BASE_URL) || "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

// ── Health ─────────────────────────────────────────────────────────────────
export const fetchHealth = () =>
  get<{ status: string; version: string; timestamp: string; uptime_ok: boolean }>("/api/v1/health");

// ── Sensors ────────────────────────────────────────────────────────────────
export interface SensorLatest {
  seq?: number;
  temperature?: number;
  humidity?: number;
  motion?: boolean;
  door_open?: boolean;
  mean_temp?: number;
  var_temp?: number;
  delta_motion?: number;
  timestamp_ms?: number;
}
export interface SensorHistory {
  ts: string;
  temperature: number;
  humidity: number;
  motion: boolean;
  mean_temp: number;
  delta_motion: number;
}
export const fetchSensorsLatest = () => get<SensorLatest>("/api/v1/sensors/latest");
export const fetchSensorsHistory = (minutes = 60) =>
  get<SensorHistory[]>(`/api/v1/sensors/history?minutes=${minutes}`);

// ── Decisions (Alerts) ─────────────────────────────────────────────────────
export interface Decision {
  id: number;
  ts: string;
  action: "notify" | "actuate_relay" | "no_action";
  confidence: number;
  reason: string;
  label: 0 | 1 | null;
}
export const fetchDecisions = (limit = 50) =>
  get<Decision[]>(`/api/v1/decisions?limit=${limit}`);
export const labelDecision = (id: number, label: 0 | 1) =>
  post<{ ok: boolean; id: number; label: number }>(`/api/v1/decisions/${id}/label`, { label });

// ── Events ─────────────────────────────────────────────────────────────────
export interface AeonEvent {
  id: number;
  ts: string;
  category: string;
  name: string;
  payload: Record<string, unknown>;
}
export const fetchEvents = (limit = 50) =>
  get<AeonEvent[]>(`/api/v1/events?limit=${limit}`);

// ── System ─────────────────────────────────────────────────────────────────
export interface SystemStatus {
  serial: {
    connected: boolean;
    port: string;
    baud: number;
    bytes_received: number;
    frames_parsed: number;
    errors: number;
    last_frame_ts: string | null;
    connected_since: string | null;
  };
  npu: {
    backend: string;
    active_models: string[];
    metadata?: Record<string, unknown>;
    metrics?: Record<string, unknown>;
  };
}
export interface PrivacyAudit {
  raw_data_transmitted_bytes: number;
  tokens_issued: number;
  audit_status: string;
}
export const fetchSystemStatus = () => get<SystemStatus>("/api/v1/system/status");
export const fetchPrivacyAudit = () => get<PrivacyAudit>("/api/v1/system/privacy");

// ── Learning ───────────────────────────────────────────────────────────────
export interface LearningStatus {
  last_train: string | null;
  is_dreaming: boolean;
  versions: Record<string, unknown>;
}
export const fetchLearningStatus = () => get<LearningStatus>("/api/v1/learning/status");
export const triggerLearning = () => post<{ ok: boolean; status: string }>("/api/v1/learning/trigger");
export const triggerDreamApi = () => post<{ ok: boolean; status: string }>("/api/v1/learning/dream");

// ── Metrics ────────────────────────────────────────────────────────────────
export interface SystemMetrics {
  db_size_bytes: number;
  features_count: number;
  decisions_count: number;
  events_count: number;
  ws_clients: number;
  cpu_pct: number;
  npu_pct: number;
  ram_pct: number;
  power_w: number;
  frames: number;
  learning_iterations: number;
  privacy_bytes_saved: number;
}
export interface NpuMetrics {
  backend: string;
  active_models: string[];
  metadata?: Record<string, unknown>;
  metrics?: Record<string, unknown>;
}
export const fetchMetricsSystem = () => get<SystemMetrics>("/api/v1/metrics/system");
export const fetchMetricsNpu = () => get<NpuMetrics>("/api/v1/metrics/npu");

// ── Knowledge Graph ────────────────────────────────────────────────────────
export interface GraphNode {
  id: string;
  type?: string;
  [key: string]: unknown;
}
export interface GraphEdge {
  src: string;
  dst: string;
  rel?: string;
  [key: string]: unknown;
}
export interface CytoscapeData {
  elements: {
    nodes: Array<{ data: { id: string; [key: string]: unknown } }>;
    edges: Array<{ data: { id?: string; source: string; target: string; [key: string]: unknown } }>;
  };
}
export const fetchGraphNodes = (type?: string) =>
  get<{ nodes: GraphNode[] }>(`/api/v1/graph/nodes${type ? `?type=${type}` : ""}`);
export const fetchGraphEdges = (rel?: string) =>
  get<{ edges: GraphEdge[] }>(`/api/v1/graph/edges${rel ? `?rel=${rel}` : ""}`);
export const fetchGraphVisualize = () => get<CytoscapeData>("/api/v1/graph/visualize");

// ── Migration ──────────────────────────────────────────────────────────────
export const fetchMigrationExport = (userId: string) =>
  get<{ user_id: string; profile: unknown }>(`/api/v1/migration/export/${encodeURIComponent(userId)}`);

// ── Voice ──────────────────────────────────────────────────────────────────
export const sendVoiceText = (text: string, userId = "default_user") =>
  post<{ transcript: string; response: string }>("/api/v1/voice/text", { text, user_id: userId });

// ── Devices ────────────────────────────────────────────────────────────────
export interface DeviceInfo {
  id: string;
  type: string;
  status: string;
  meta: Record<string, unknown>;
}
export const fetchDevices = () => get<DeviceInfo[]>("/api/v1/devices");
