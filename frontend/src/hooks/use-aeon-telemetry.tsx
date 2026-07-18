import React, { useEffect, useState, useCallback, useRef, createContext, useContext } from "react";

export interface TelemetryState {
  serialStatus: {
    connected: boolean;
    port: string;
    baud: number;
    frameRate: number;
    eepromUsagePct: number;
    lastCheckpointSec: number;
    temperature: number | null;
    humidity: number | null;
    motionState: string;
  };
  snapdragonStatus: {
    connected: boolean;
    npuActive: boolean;
    modelName: string;
    latencyMs: number;
    throughputFps: number;
    memoryMb: number;
    tokensVerified: number;
    powerState: string;
    executionProvider: string;
    cpuPct: number;
    npuPctEstimated: number;
  };
  continuousLearning: {
    progressPct: number;
    falseAlarmsFlagged: number;
    sensitivityThreshold: number;
    lastAdaptationSec: number;
    status: string;
  };
  dreamState: {
    active: boolean;
    eventsReplayed: number;
    compressionPct: number;
    beforeLatencyMs: number;
    afterLatencyMs: number;
    lastRunTime: string;
  };
  voiceAssistant: {
    sarvamConnected: boolean;
    language: string;
    isListening: boolean;
    isSpeaking: boolean;
    lastQuery: string;
    lastResponse: string;
  };
  privacyMesh: {
    rawBytesSent: number;
    capabilityTokensIssued: number;
    lastAuditSec: number;
    auditLog: Array<{
      time: string;
      token: string;
      event: string;
      status: string;
    }>;
  };
  knowledgeGraph: {
    nodesCount: number;
    edgesCount: number;
    lastNodeAdded: string;
  };
  migrationState: {
    status: string;
    qrCodePayload: string;
    targetDeviceId: string;
  };
  events?: Array<{
    id: number;
    time: string;
    label: string;
    category: string;
    tint: string;
  }>;
}

const DISCONNECTED_STATE: TelemetryState = {
  serialStatus: {
    connected: false,
    port: "???",
    baud: 0,
    frameRate: 0,
    eepromUsagePct: 0,
    lastCheckpointSec: 0,
    temperature: null,
    humidity: null,
    motionState: "Arduino disconnected",
  },
  snapdragonStatus: {
    connected: false,
    npuActive: false,
    modelName: "Model not loaded",
    latencyMs: 0,
    throughputFps: 0,
    memoryMb: 0,
    tokensVerified: 0,
    powerState: "???",
    executionProvider: "UNAVAILABLE",
    cpuPct: 0,
    npuPctEstimated: 0,
  },
  continuousLearning: {
    progressPct: 0,
    falseAlarmsFlagged: 0,
    sensitivityThreshold: 0,
    lastAdaptationSec: 0,
    status: "Waiting for backend...",
  },
  dreamState: {
    active: false,
    eventsReplayed: 0,
    compressionPct: 0,
    beforeLatencyMs: 0,
    afterLatencyMs: 0,
    lastRunTime: "Never",
  },
  voiceAssistant: {
    sarvamConnected: false,
    language: "???",
    isListening: false,
    isSpeaking: false,
    lastQuery: "",
    lastResponse: "",
  },
  privacyMesh: {
    rawBytesSent: 0,
    capabilityTokensIssued: 0,
    lastAuditSec: 0,
    auditLog: [],
  },
  knowledgeGraph: {
    nodesCount: 0,
    edgesCount: 0,
    lastNodeAdded: "Knowledge graph initializing",
  },
  migrationState: {
    status: "idle",
    qrCodePayload: "",
    targetDeviceId: "Awaiting scan",
  },
  events: [],
};

const DEFAULT_MOCK_TELEMETRY: TelemetryState = {
  serialStatus: {
    connected: true,
    port: "COM3",
    baud: 115200,
    frameRate: 0,
    eepromUsagePct: 42,
    lastCheckpointSec: 12,
    temperature: 21.6,
    humidity: 48.0,
    motionState: "Idle",
  },
  snapdragonStatus: {
    connected: true,
    npuActive: false,
    modelName: "QNN (Hexagon NPU)",
    latencyMs: 8.5,
    throughputFps: 120,
    memoryMb: 256,
    tokensVerified: 1284,
    powerState: "15.0W Snapdragon Edge Draw",
    executionProvider: "QNN_HTP",
    cpuPct: 12.5,
    npuPctEstimated: 5.0,
  },
  continuousLearning: {
    progressPct: 85,
    falseAlarmsFlagged: 0,
    sensitivityThreshold: 0.75,
    lastAdaptationSec: 0,
    status: "On-Device Adaptation Active",
  },
  dreamState: {
    active: false,
    eventsReplayed: 4200,
    compressionPct: 35,
    beforeLatencyMs: 14.5,
    afterLatencyMs: 8.5,
    lastRunTime: "03:00 AM",
  },
  voiceAssistant: {
    sarvamConnected: true,
    language: "hi-IN",
    isListening: false,
    isSpeaking: false,
    lastQuery: "System Ready",
    lastResponse: "System Ready",
  },
  privacyMesh: {
    rawBytesSent: 0,
    capabilityTokensIssued: 52,
    lastAuditSec: 12,
    auditLog: [
      { time: "09:43", token: "CAP-1032", event: "Person alert token issued", status: "verified" },
      { time: "09:12", token: "CAP-1031", event: "Door insight granted", status: "verified" },
      { time: "08:58", token: "CAP-1030", event: "Env token issued", status: "verified" },
      { time: "08:41", token: "SYS-0041", event: "Chain re-verified after boot", status: "ok" },
    ],
  },
  knowledgeGraph: {
    nodesCount: 24,
    edgesCount: 56,
    lastNodeAdded: "Integration Completed",
  },
  migrationState: {
    status: "idle",
    qrCodePayload: "aeon://identity/v1/export?token=ready",
    targetDeviceId: "Snapdragon-Node-2",
  },
  events: [
    { id: 1, time: "09:41", label: "Motion detected", category: "security", tint: "var(--aeon-purple)" },
    { id: 2, time: "09:43", label: "Capability token issued", category: "auth", tint: "var(--aeon-blue)" },
    { id: 3, time: "09:45", label: "User marked false alarm", category: "security", tint: "oklch(0.7 0.18 30)" },
    { id: 4, time: "09:47", label: "State checkpoint saved", category: "system", tint: "oklch(0.7 0.15 150)" },
    { id: 5, time: "09:50", label: "Dream State queued", category: "learning", tint: "var(--aeon-pink)" },
  ],
};

const isDemoModeEnabled = import.meta.env.VITE_DEMO_MODE === "true";
const INITIAL_STATE = isDemoModeEnabled ? DEFAULT_MOCK_TELEMETRY : DISCONNECTED_STATE;

export function useAeonTelemetry() {
  const [telemetry, setTelemetry] = useState<TelemetryState>(INITIAL_STATE);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const resolveWsUrl = () => {
      // Prefer explicit env var
      const envUrl = (import.meta as any).env?.VITE_WS_URL;
      if (envUrl) return envUrl;

      // Try to parse VITE_API_BASE_URL
      const baseApiUrl = (import.meta as any).env?.VITE_API_BASE_URL;
      if (baseApiUrl) {
        try {
          const url = new URL(baseApiUrl);
          const wsProto = url.protocol === "https:" ? "wss:" : "ws:";
          return `${wsProto}//${url.host}/ws/dashboard`;
        } catch (e) {
          // ignore error
        }
      }

      // Default fallback
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      const hostname = window.location.hostname || "localhost";
      return `${proto}//${hostname}:8000/ws/dashboard`;
    };

    const wsUrl = resolveWsUrl();
    let active = true;
    let reconnectTimeout: number;

    const connect = () => {
      console.log(`Connecting to ÆON WebSocket at: ${wsUrl}`);
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        if (!active) return;
        console.log("Connected to ÆON WebSocket");
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        if (!active) return;
        try {
          console.log("WebSocket message received:", event.data);
          const message = JSON.parse(event.data);
          console.log("Parsed message type:", message.type);
          if (message.type === "telemetry" && message.payload) {
            console.log("Setting telemetry state:", message.payload);
            setTelemetry(message.payload);
          }
        } catch (err) {
          console.error("Failed to parse WebSocket message:", err);
        }
      };

      ws.onerror = (err) => {
        console.error("WebSocket error:", err);
      };

      ws.onclose = () => {
        if (!active) return;
        console.log("Disconnected from ÆON WebSocket, retrying in 3s...");
        setIsConnected(false);
        setTelemetry(isDemoModeEnabled ? DEFAULT_MOCK_TELEMETRY : DISCONNECTED_STATE);
        reconnectTimeout = window.setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      active = false;
      if (socketRef.current) {
        socketRef.current.close();
      }
      clearTimeout(reconnectTimeout);
    };
  }, []);

  const sendCommand = useCallback((type: string, payload: any = {}) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type, payload }));
      return true;
    }
    console.warn("WebSocket not connected. Command dropped:", { type, payload });
    return false;
  }, []);

  const triggerDream = useCallback(() => {
    return sendCommand("trigger_dream");
  }, [sendCommand]);

  const sendVoiceQuery = useCallback((text: string) => {
    return sendCommand("voice_query", { text });
  }, [sendCommand]);

  const flagFalseAlarm = useCallback((token: string) => {
    return sendCommand("false_alarm", { token });
  }, [sendCommand]);

  const triggerMigration = useCallback(() => {
    return sendCommand("trigger_migration");
  }, [sendCommand]);

  const startListening = useCallback(() => {
    return sendCommand("start_listening");
  }, [sendCommand]);

  return {
    telemetry,
    isConnected,
    triggerDream,
    sendVoiceQuery,
    flagFalseAlarm,
    triggerMigration,
    startListening,
  };
}

export type UseAeonTelemetryReturn = ReturnType<typeof useAeonTelemetry>;

const AeonTelemetryContext = createContext<UseAeonTelemetryReturn | null>(null);

export function AeonTelemetryProvider({ children }: { children: React.ReactNode }) {
  const value = useAeonTelemetry();
  return (
    <AeonTelemetryContext.Provider value={value}>
      {children}
    </AeonTelemetryContext.Provider>
  );
}

export function useAeon() {
  const context = useContext(AeonTelemetryContext);
  if (!context) {
    throw new Error("useAeon must be used within an AeonTelemetryProvider");
  }
  return context;
}
