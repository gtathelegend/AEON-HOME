# API Reference — REST & WebSocket Specifications

This document catalogs the REST API endpoints and WebSocket interfaces exposed by the ÆON Home Host application.

---

## 1. REST API Index

### 1. Unified Health Summary
- **Endpoint**: `GET /api/v1/health`
- **Purpose**: Retrieve overall system node, API, and serial connection health metrics.
- **Response Example**:
  ```json
  {
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2026-07-19T02:15:00Z",
    "uptime_ok": true
  }
  ```

### 2. Device Inventory Mirror
- **Endpoint**: `GET /api/v1/devices`
- **Purpose**: Get current status, capabilities, latencies, and connectivity state of all registered edge devices.
- **Response Example**:
  ```json
  [
    {
      "device_id": "sentinel_01",
      "type": "sentinel",
      "connected": true,
      "health": "healthy",
      "reliability": 0.98,
      "avg_latency_ms": 12.5
    }
  ]
  ```

### 3. Decisions Log
- **Endpoint**: `GET /api/v1/decisions?limit=5`
- **Purpose**: Retrieve history of selected actions and associated reasoning graphs.
- **Response Example**:
  ```json
  [
    {
      "id": 1240,
      "action": "ON",
      "confidence": 0.89,
      "reason": "MANUAL_OVERRIDE",
      "timestamp": "2026-07-19T02:14:00Z"
    }
  ]
  ```

---

## 2. WebSocket Gateways

### 1. Device Gateway (`/ws/device`)
Enables direct bi-directional serial/wifi communication with the Arduino Uno Q. Requires HMAC signature wrapping for write calls.

### 2. Dashboard Broadcast (`/ws/dashboard`)
Broadcasts real-time events (`sensor_update`, `decision_generated`, `event_timeline`) to PWA dashboards. Requires zero authentication for read-only telemetry.
