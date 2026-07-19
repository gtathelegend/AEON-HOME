# core/context/providers.py

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict

from core.interfaces.adaptive import IContextProvider


class TimeContextProvider(IContextProvider):
    """Temporal context provider (hour, day of week, is_weekend, epoch)."""

    async def get_context(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        return {
            "timestamp": now.isoformat(),
            "hour": now.hour,
            "minute": now.minute,
            "day_of_week": now.strftime("%A"),
            "is_weekend": now.weekday() >= 5,
            "epoch_s": int(time.time()),
        }


class SensorContextProvider(IContextProvider):
    """Environmental context provider consuming latest sensor frames from WebSocketBus."""

    def __init__(self, ws_bus: Any) -> None:
        self._ws_bus = ws_bus

    async def get_context(self) -> Dict[str, Any]:
        processor = getattr(self._ws_bus, "sensor_processor", None)
        latest = processor.get_latest() if processor else None
        if not latest:
            return {
                "temperature": 21.0,
                "humidity": 50.0,
                "motion": False,
                "door_open": False,
                "mean_temp": 21.0,
                "var_temp": 0.0,
                "delta_motion": 0.0,
                "valid": False,
            }
        return {
            "temperature": latest.get("temperature", 21.0),
            "humidity": latest.get("humidity", 50.0),
            "motion": bool(latest.get("motion", False)),
            "door_open": bool(latest.get("door_open", False)),
            "mean_temp": latest.get("mean_temp", 21.0),
            "var_temp": latest.get("var_temp", 0.0),
            "delta_motion": latest.get("delta_motion", 0.0),
            "valid": True,
        }


class DeviceContextProvider(IContextProvider):
    """Device context provider tracking active relays and registered devices."""

    def __init__(self, ws_bus: Any) -> None:
        self._ws_bus = ws_bus

    async def get_context(self) -> Dict[str, Any]:
        bridge = getattr(self._ws_bus, "serial_bridge", None)
        registry = getattr(self._ws_bus, "device_registry", None)
        
        serial_status = bridge.get_status() if bridge else {}
        devices = registry.list_devices() if registry else []
        return {
            "serial_connected": serial_status.get("connected", False),
            "serial_port": serial_status.get("port", "unknown"),
            "registered_devices_count": len(devices),
            "fan_speed_percent": 0,
            "fan_pwm": 0,
        }


class UserContextProvider(IContextProvider):
    """User context provider tracking active profiles."""

    def __init__(self, ws_bus: Any) -> None:
        self._ws_bus = ws_bus

    async def get_context(self) -> Dict[str, Any]:
        identity = getattr(self._ws_bus, "identity_manager", None)
        users = await identity.list_users() if identity else []
        user_id = users[0]["id"] if users else "default_user"
        return {
            "active_user_id": user_id,
            "authorized_users": [u["id"] for u in users],
        }


class SystemContextProvider(IContextProvider):
    """System context provider for Snapdragon host resource statistics."""

    async def get_context(self) -> Dict[str, Any]:
        import sys
        return {
            "uptime_s": int(time.perf_counter()),
            "network_online": True,
            "platform": sys.platform,
        }


class RuntimeContextProvider(IContextProvider):
    """Runtime context provider exposing model manager statistics and versions."""

    def __init__(self, ws_bus: Any) -> None:
        self._ws_bus = ws_bus

    async def get_context(self) -> Dict[str, Any]:
        manager = getattr(self._ws_bus, "model_manager", None)
        if not manager:
            return {
                "active_model_id": "none",
                "active_model_version": 0,
                "model_confidence": 0.0,
                "error_rate": 0.0,
            }
        status = manager.get_deployment_status()
        stats = manager.runtime_statistics.to_dict() if manager.runtime_statistics else {}
        active = status.get("active_model") or {}
        
        return {
            "active_model_id": active.get("model_id", "none"),
            "active_model_version": active.get("version", 0),
            "model_confidence": stats.get("avg_confidence", 0.0),
            "error_rate": stats.get("error_count", 0) / max(1, stats.get("total_inference_count", 1)),
        }
