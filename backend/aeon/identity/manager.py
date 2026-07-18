"""
aeon/identity/manager.py — Identity and user profile management.

Handles user creation, deletion, retrieval of profiles and preferences,
and identity export bundles for migration.
"""

from __future__ import annotations

import json
import structlog
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aeon.graph.knowledge_graph import KnowledgeGraph

log = structlog.get_logger(__name__)


class IdentityManager:
    def __init__(self, graph: "KnowledgeGraph") -> None:
        self._graph = graph

    async def create_user(self, user_id: str, display_name: str) -> None:
        await self._graph.upsert_node(user_id, type="user", display_name=display_name)
        log.info("identity.user_created", user_id=user_id)

    async def list_users(self) -> list[dict[str, Any]]:
        users = []
        for n, d in self._graph._graph.nodes(data=True):
            if d.get("type") == "user":
                users.append({"id": n, "display_name": d.get("display_name", "Unknown")})
        return users

    async def get_user_profile(self, user_id: str) -> dict[str, Any]:
        prefs     = await self._graph.get_preferences(user_id)
        node_data = {}
        if user_id in self._graph._graph:
            node_data = self._graph._graph.nodes[user_id]
        return {
            "user_id":      user_id,
            "display_name": node_data.get("display_name", "Unknown"),
            "preferences":  prefs,
        }

    async def export(self, user_id: str) -> dict[str, Any]:
        """
        Export a user subgraph as a migration bundle.
        Returns a dict with:
          qr_payload  — URL-safe string suitable for QR encoding
          node_count  — number of nodes exported
          bundle      — full serialised graph data (for import)
        """
        from aeon.config.settings import settings

        profile = await self._graph.export_profile(user_id)
        node_count = len(profile.get("nodes", []))

        # Build a compact URL payload for the QR code
        profile_json = json.dumps(profile, separators=(",", ":"), sort_keys=True)
        import hashlib
        digest = hashlib.sha256(profile_json.encode()).hexdigest()[:12]
        qr_payload = (
            f"aeon://identity/v1/import"
            f"?src={settings.device_id}"
            f"&user={user_id}"
            f"&hash={digest}"
        )

        log.info("identity.export", user_id=user_id, nodes=node_count)
        return {
            "qr_payload":  qr_payload,
            "node_count":  node_count,
            "bundle":      profile,
        }
