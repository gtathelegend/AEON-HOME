"""
aeon/api/app.py — FastAPI application factory.

All routes are prefixed /api/v1.
The dashboard PWA and mobile client consume these endpoints.

Authentication: Bearer JWT capability tokens (issued by aeon.auth.tokens).
Privacy:        Endpoints return processed insights, never raw sensor data.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.aeon.api.routes import devices as devices_router
from backend.aeon.api.routes import decisions as decisions_router
from backend.aeon.api.routes import graph as graph_router
from backend.aeon.api.routes import migration as migration_router
from backend.aeon.api.routes import voice as voice_router
from backend.aeon.api.routes import health as health_router
from backend.aeon.api.routes import sensors as sensors_router
from backend.aeon.api.routes import events as events_router
from backend.aeon.api.routes import metrics_api as metrics_router
from backend.aeon.api.routes import learning_api as learning_router
from backend.aeon.api.routes import system as system_router
from backend.aeon.api.routes import models_api as models_router
from backend.aeon.api.routes import adaptive_api as adaptive_router
from backend.aeon.api.routes import cognitive_api as cognitive_router

def create_app(
    *, 
    memory, 
    graph, 
    ws_bus, 
    policy, 
    metrics, 
    sensor_processor,
    event_processor,
    model_manager,
    learning_loop,
    serial_bridge,
    serial_writer,
    identity_manager,
    device_registry,
    voice_manager,
    deployment_service=None,
) -> FastAPI:
    app = FastAPI(
        title="ÆON Home API",
        version="1.0.0",
        description="Persistent Edge Intelligence Platform — Snapdragon X Elite",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    # ── CORS (PWA dashboard on same machine or LAN) ───────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],   # tighten in production
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Inject shared dependencies via app.state ──────────────────────────────
    app.state.memory  = memory
    app.state.graph   = graph
    app.state.ws_bus  = ws_bus
    app.state.policy  = policy
    app.state.metrics = metrics
    app.state.sensor_processor = sensor_processor
    app.state.event_processor  = event_processor
    app.state.model_manager    = model_manager
    app.state.learning_loop    = learning_loop
    app.state.serial_bridge    = serial_bridge
    app.state.serial_writer    = serial_writer
    app.state.identity_manager = identity_manager
    app.state.device_registry     = device_registry
    app.state.voice_manager       = voice_manager
    app.state.deployment_service  = deployment_service

    # ── Register routers ──────────────────────────────────────────────────────
    app.include_router(health_router.router,     prefix="/api/v1")
    app.include_router(devices_router.router,    prefix="/api/v1")
    app.include_router(decisions_router.router,  prefix="/api/v1")
    app.include_router(graph_router.router,      prefix="/api/v1")
    app.include_router(migration_router.router,  prefix="/api/v1")
    app.include_router(voice_router.router,      prefix="/api/v1")
    app.include_router(sensors_router.router,    prefix="/api/v1")
    app.include_router(events_router.router,     prefix="/api/v1")
    app.include_router(metrics_router.router,    prefix="/api/v1")
    app.include_router(learning_router.router,   prefix="/api/v1")
    app.include_router(system_router.router,     prefix="/api/v1")
    app.include_router(models_router.router,     prefix="/api/v1")
    app.include_router(adaptive_router.router,   prefix="/api/v1")
    app.include_router(cognitive_router.router,  prefix="/api/v1")


    from backend.aeon.api.routes import gateway as gateway_router
    app.include_router(gateway_router.router)  # Mounted at root for /ws/device

    return app
