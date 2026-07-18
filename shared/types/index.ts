/**
 * shared/types/index.ts
 *
 * TypeScript types shared between the frontend dashboard and
 * any TypeScript tooling that consumes the backend API.
 *
 * Keep in sync with:
 *   - shared/schemas/*.schema.json
 *   - backend/aeon/serial/parser.py  (FeatureFrame dataclass)
 *   - backend/aeon/auth/tokens.py    (CapabilityToken)
 */

// ── Feature frame (mirrors FeatureFrame in parser.py) ────────────────────────

export interface FeatureFrame {
  seq:          number;
  timestamp_ms: number;
  temperature:  number;
  humidity:     number;
  motion:       boolean;
  door_open:    boolean;
  mean_temp:    number;
  var_temp:     number;
  delta_motion: number;
}

// ── Capability token ──────────────────────────────────────────────────────────

export interface CapabilityTokenPayload {
  jti:        string;
  sub:        string;          // device_id
  capability: string;          // e.g. "presence.detected"
  confidence: number;          // 0–1
  reason:     string;
  iat:        number;          // unix timestamp
  exp:        number;          // unix timestamp
}

// ── Policy decision ───────────────────────────────────────────────────────────

export type PolicyAction = "notify" | "actuate_relay" | "no_action";

export interface PolicyDecision {
  id:         number;
  ts:         string;          // ISO-8601
  frame_seq:  number;
  action:     PolicyAction;
  confidence: number;
  reason:     string;
  label:      0 | 1 | null;   // user feedback
}

// ── WebSocket event envelope ──────────────────────────────────────────────────

export interface WsEvent<T = unknown> {
  type:    string;
  ts:      string;             // ISO-8601
  payload: T;
}

export interface WsDecisionEvent extends WsEvent<{
  action:     PolicyAction;
  confidence: number;
  reason:     string;
  seq:        number;
}> { type: "decision"; }

// ── Device registry ───────────────────────────────────────────────────────────

export type DeviceType =
  | "arduino_sentinel"
  | "snapdragon_pc"
  | "mobile"
  | "cloud_ai100";

export type DeviceStatus = "online" | "offline" | "idle" | "unknown";

export interface DeviceInfo {
  id:     string;
  type:   DeviceType;
  status: DeviceStatus;
  meta:   Record<string, unknown>;
}

// ── Knowledge graph profile ───────────────────────────────────────────────────

export interface GraphNode {
  id:    string;
  type:  string;
  [key: string]: unknown;
}

export interface GraphEdge {
  source: string;
  target: string;
  rel:    string;
  [key: string]: unknown;
}

export interface UserProfile {
  nodes: GraphNode[];
  links: GraphEdge[];
}

// ── Migration ─────────────────────────────────────────────────────────────────

export interface MigrationExport {
  user_id: string;
  profile: UserProfile;
}

// ── API Graph Edge (as returned by /api/v1/graph/edges) ─────────────────────────

export interface ApiGraphEdge {
  src:  string;
  dst:  string;
  rel?: string;
  [key: string]: unknown;
}

// ── Shared Protocol Constants ──────────────────────────────────────────────────

export const AEON_MAGIC_0 = 0xAE;
export const AEON_MAGIC_1 = 0x01;

export const AEON_TYPE_FEATURE_FRAME = 0x01;
export const AEON_TYPE_EVENT         = 0x02;
export const AEON_TYPE_COMMAND       = 0x10;
export const AEON_TYPE_ACK           = 0xFF;

export const DEFAULT_BAUD_RATE = 115200;
export const DEFAULT_DEVICE_ID = "aeon-home-001";

