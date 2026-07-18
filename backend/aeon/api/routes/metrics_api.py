"""
GET /api/v1/metrics/system
GET /api/v1/metrics/npu
WS  /api/v1/metrics/stream
"""
from __future__ import annotations

import asyncio
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["metrics"])

@router.get("/metrics/system")
async def system_metrics(request: Request):
    memory = request.app.state.memory
    stats = await memory.get_system_stats()
    
    ws_bus = request.app.state.ws_bus
    stats["ws_clients"] = len(ws_bus._clients)
    
    # Import prometheus values to return via REST
    from aeon.metrics.exporter import (
        sys_cpu_utilization, sys_npu_utilization, sys_ram_utilization, sys_power_draw_w,
        frames_total, decisions_total, anomaly_score, learning_train_total, privacy_bytes_saved
    )
    
    stats["cpu_pct"] = sys_cpu_utilization._value.get()
    stats["npu_pct"] = sys_npu_utilization._value.get()
    stats["ram_pct"] = sys_ram_utilization._value.get()
    stats["power_w"] = sys_power_draw_w._value.get()
    stats["frames"] = frames_total._value.get()
    stats["learning_iterations"] = learning_train_total._value.get()
    stats["privacy_bytes_saved"] = privacy_bytes_saved._value.get()
    
    return stats

@router.get("/metrics/npu")
async def npu_metrics(request: Request):
    models = request.app.state.model_manager
    return models.get_status()

@router.get("/metrics/history")
async def metrics_history(request: Request, minutes: int = 60):
    """
    Return time-series sensor + inference data for dashboard charts.
    All values come from the SQLite memory store — no synthetic data.
    """
    memory = request.app.state.memory
    sensor_rows = await memory.get_sensor_history(minutes=minutes)

    # Also pull decisions for latency approximation
    model_mgr = request.app.state.model_manager
    npu_stats = model_mgr.get_status().get("metrics", {})

    return {
        "sensor_history": sensor_rows,
        "npu_stats": npu_stats,
        "minutes": minutes,
    }


@router.websocket("/metrics/stream")
async def metrics_stream(websocket: WebSocket):
    await websocket.accept()
    app = websocket.app
    try:
        while True:
            # Gather comprehensive real-time payload
            memory = app.state.memory
            stats = await memory.get_system_stats()
            
            from aeon.metrics.exporter import (
                sys_cpu_utilization, sys_npu_utilization, sys_ram_utilization, sys_power_draw_w,
                frames_total, learning_train_total, privacy_bytes_saved
            )
            
            payload = {
                "system": {
                    "cpu_pct": sys_cpu_utilization._value.get(),
                    "npu_pct": sys_npu_utilization._value.get(),
                    "ram_pct": sys_ram_utilization._value.get(),
                    "power_w": sys_power_draw_w._value.get(),
                    "db_size": stats.get("db_size_bytes", 0)
                },
                "models": app.state.model_manager.get_status(),
                "learning": {
                    "iterations": learning_train_total._value.get(),
                    "privacy_bytes_saved": privacy_bytes_saved._value.get(),
                },
                "serial": {
                    "frames_received": frames_total._value.get()
                }
            }
            
            await websocket.send_json(payload)
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass
