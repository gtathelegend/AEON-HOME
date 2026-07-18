"""
aeon/memory/seed.py — Database seeding for default AEON Home setup.
"""

from __future__ import annotations

import json
import structlog
from datetime import datetime, timedelta

log = structlog.get_logger(__name__)


async def seed_database_if_empty(memory, graph) -> None:
    """Check database counts, seed default setup if empty."""
    from aeon.config.settings import settings
    stats = await memory.get_system_stats()
    
    # 1. Seed Core Knowledge Graph Entities (always initialized on empty graph)
    if graph._graph.number_of_nodes() == 0:
        log.info("database.seeding.graph", message="Knowledge graph is empty, seeding default layout")
        # Add Owner User
        await graph.add_user("user_1", name="Vedaang", role="owner")
        
        # Add Rooms
        await graph.add_room("living_room", name="Living Room")
        await graph.add_room("bedroom", name="Bedroom")
        
        # Add Devices
        await graph.add_device("arduino", name="Arduino Sentinel", device_type="sentinel")
        await graph.add_device("esp8266", name="ESP8266 Wireless Gateway", device_type="gateway")
        await graph.add_device("aipc", name="Snapdragon X Elite Edge Engine", device_type="edge_engine")
        await graph.add_device("phone", name="Mobile PWA", device_type="mobile")
        
        # Link ownership
        await graph.link_owns("user_1", "arduino")
        await graph.link_owns("user_1", "esp8266")
        await graph.link_owns("user_1", "aipc")
        await graph.link_owns("user_1", "phone")
        
        # Link locations
        await graph.link_located_in("arduino", "living_room")
        await graph.link_located_in("esp8266", "living_room")
        await graph.link_located_in("aipc", "living_room")
        await graph.link_located_in("phone", "bedroom")
        
        # Seed preference settings
        await graph.update_preference("user_1", "privacy_mode", "active")
        await graph.update_preference("user_1", "night_mode", "inactive")
        log.info("database.seeding.graph.complete")

    # 2. Seed System Events (Timeline) and Decisions (Alerts) ONLY in Demo Mode
    if settings.aeon_demo_mode:
        if stats.get("events_count", 0) == 0:
            log.info("database.seeding.events", message="Events table is empty, seeding default timeline logs (Demo Mode)")
            now = datetime.utcnow()
            default_events = [
                ("security", "Motion detected", {"time": (now - timedelta(minutes=9)).strftime("%H:%M"), "room": "Hallway"}),
                ("auth", "Capability token issued", {"time": (now - timedelta(minutes=7)).strftime("%H:%M"), "token_id": "CAP-1032"}),
                ("security", "User marked false alarm", {"time": (now - timedelta(minutes=5)).strftime("%H:%M"), "token_id": "CAP-1032"}),
                ("system", "State checkpoint saved", {"time": (now - timedelta(minutes=3)).strftime("%H:%M"), "size_kb": 4.2}),
                ("learning", "Dream State queued", {"time": (now - timedelta(minutes=1)).strftime("%H:%M"), "reason": "Low activity"}),
            ]
            for cat, name, payload in default_events:
                await memory.log_event(cat, name, payload)
            log.info("database.seeding.events.complete")

        if stats.get("decisions_count", 0) == 0:
            log.info("database.seeding.decisions", message="Decisions table is empty, seeding default alerts (Demo Mode)")
            now = datetime.utcnow()
            decisions = [
                ((now - timedelta(minutes=7)).isoformat(), 1032, "notify", 0.94, "Person detected in hallway"),
                ((now - timedelta(minutes=38)).isoformat(), 1031, "notify", 0.82, "Front door left open 4 min"),
                ((now - timedelta(minutes=52)).isoformat(), 1030, "notify", 0.72, "Living room temperature spike"),
                ((now - timedelta(minutes=69)).isoformat(), 1029, "actuate_relay", 0.99, "Power interruption recovered"),
            ]
            for ts, seq, action, confidence, reason in decisions:
                await memory._db.execute(
                    "INSERT INTO decisions (ts,frame_seq,action,confidence,reason) VALUES (?,?,?,?,?)",
                    (ts, seq, action, confidence, reason)
                )
            await memory._db.commit()
            log.info("database.seeding.decisions.complete")
