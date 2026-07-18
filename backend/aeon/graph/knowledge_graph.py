"""
aeon/graph/knowledge_graph.py — On-device knowledge graph.

Stores and queries the user's preference model, device relationships,
room context, and behavioural patterns.

Implementation: NetworkX in-memory graph + SQLite persistence via MemoryStore.
The graph is rebuilt from SQLite on every boot so it survives power loss.

Node types:
  user     — identity node (owner / guest)
  device   — physical device (Arduino, AI PC, phone)
  room     — spatial context
  event    — timestamped sensor event
  rule     — policy rule derived from learning

Edge types:
  owns         (user → device)
  located_in   (device → room)
  triggered    (event → device)
  prefers      (user → {setting, value})
  implies      (event → rule)
"""

from __future__ import annotations

import asyncio
import structlog
from typing import Any

import networkx as nx

log = structlog.get_logger(__name__)


class KnowledgeGraph:
    def __init__(self, store) -> None:
        self._store = store
        self._graph = nx.MultiDiGraph()
        self._lock  = asyncio.Lock()

    async def init(self) -> None:
        """Load persisted graph from SQLite."""
        nodes, edges = await self._store.load_graph()
        for node_id, attrs in nodes:
            self._graph.add_node(node_id, **attrs)
        for src, dst, attrs in edges:
            self._graph.add_edge(src, dst, **attrs)
        log.info("graph.loaded",
                 nodes=self._graph.number_of_nodes(),
                 edges=self._graph.number_of_edges())

    async def upsert_node(self, node_id: str, **attrs: Any) -> None:
        async with self._lock:
            self._graph.add_node(node_id, **attrs)
            await self._store.save_node(node_id, attrs)

    async def upsert_edge(self, src: str, dst: str, rel: str, **attrs: Any) -> None:
        async with self._lock:
            self._graph.add_edge(src, dst, rel=rel, **attrs)
            await self._store.save_edge(src, dst, rel, attrs)

    # ── Schema Methods ────────────────────────────────────────────────────────
    
    async def add_user(self, user_id: str, name: str, role: str = "owner") -> None:
        await self.upsert_node(user_id, type="user", name=name, role=role)

    async def add_room(self, room_id: str, name: str) -> None:
        await self.upsert_node(room_id, type="room", name=name)

    async def add_device(self, device_id: str, name: str, device_type: str) -> None:
        await self.upsert_node(device_id, type="device", name=name, device_type=device_type)

    async def add_event(self, event_id: str, event_type: str, payload: dict) -> None:
        await self.upsert_node(event_id, type="event", event_type=event_type, payload=payload)
        
    async def add_policy(self, policy_id: str, rule: dict) -> None:
        await self.upsert_node(policy_id, type="policy", rule=rule)

    async def link_located_in(self, entity_id: str, room_id: str) -> None:
        await self.upsert_edge(entity_id, room_id, rel="located_in")

    async def link_owns(self, user_id: str, device_id: str) -> None:
        await self.upsert_edge(user_id, device_id, rel="owns")

    async def link_triggered(self, event_id: str, device_id: str) -> None:
        await self.upsert_edge(event_id, device_id, rel="triggered")

    async def link_implies(self, event_id: str, policy_id: str) -> None:
        await self.upsert_edge(event_id, policy_id, rel="implies")

    # ── Preferences ───────────────────────────────────────────────────────────
    
    async def get_preferences(self, user_id: str) -> dict[str, Any]:
        """Return all preference edges for a user as {setting: value}."""
        async with self._lock:
            prefs: dict[str, Any] = {}
            if user_id not in self._graph:
                return prefs
            for _, dst, data in self._graph.out_edges(user_id, data=True):
                if data.get("rel") == "prefers":
                    prefs[dst] = data.get("value")
            return prefs

    async def update_preference(
        self, user_id: str, setting: str, value: Any
    ) -> None:
        node_id = f"pref:{user_id}:{setting}"
        await self.upsert_node(node_id, type="preference", setting=setting)
        await self.upsert_edge(user_id, node_id, rel="prefers", value=value)

    def get_active_rules_sync(self) -> list[dict]:
        """Synchronous read for use inside the thread-pool policy step."""
        return [
            {**data, "src": src, "dst": dst}
            for src, dst, data in self._graph.edges(data=True)
            if data.get("rel") == "implies"
        ]

    # ── Migration ─────────────────────────────────────────────────────────────
    
    async def export_profile(self, user_id: str) -> dict:
        """Serialise user subgraph for identity migration."""
        async with self._lock:
            if user_id not in self._graph:
                return {}
            sub = nx.ego_graph(self._graph, user_id, radius=2)
            return nx.node_link_data(sub)

    async def import_profile(self, profile: dict) -> None:
        """Merge an imported profile into the local graph."""
        async with self._lock:
            imported = nx.node_link_graph(profile)
            self._graph = nx.compose(self._graph, imported)
            # Persist all new nodes and edges
            for node_id, attrs in imported.nodes(data=True):
                await self._store.save_node(node_id, attrs)
            for src, dst, attrs in imported.edges(data=True):
                await self._store.save_edge(src, dst, attrs.get("rel", ""), attrs)

    # ── Visualization & Search & Reasoning ────────────────────────────────────

    async def export_cytoscape(self) -> dict:
        """Export the graph to Cytoscape JSON for frontend visualization."""
        async with self._lock:
            cy_data = nx.cytoscape_data(self._graph)
            
            # Prune payload if graph is huge
            # Max 500 event nodes for visualization
            if len(cy_data["elements"]["nodes"]) > 1000:
                nodes_to_keep = []
                event_count = 0
                for n in cy_data["elements"]["nodes"]:
                    ntype = n["data"].get("type")
                    if ntype == "event":
                        if event_count < 500:
                            nodes_to_keep.append(n)
                            event_count += 1
                    else:
                        nodes_to_keep.append(n)
                
                kept_ids = {n["data"]["id"] for n in nodes_to_keep}
                edges_to_keep = [
                    e for e in cy_data["elements"]["edges"] 
                    if e["data"]["source"] in kept_ids and e["data"]["target"] in kept_ids
                ]
                cy_data["elements"]["nodes"] = nodes_to_keep
                cy_data["elements"]["edges"] = edges_to_keep
                
            return cy_data

    async def find_shortest_path(self, src: str, dst: str) -> list[str]:
        """Find topological relationship via shortest path."""
        async with self._lock:
            try:
                # Undirected path finding usually makes more sense for context
                undirected = self._graph.to_undirected()
                return nx.shortest_path(undirected, source=src, target=dst)
            except nx.NetworkXNoPath:
                return []
            except nx.NodeNotFound:
                return []

    async def infer_context(self, user_id: str) -> dict[str, Any]:
        """
        Simple graph traversal reasoning.
        E.g., If User -> owns -> Phone -> located_in -> Room, infer User is near Room.
        """
        async with self._lock:
            inferred = {"near_rooms": [], "active_devices": []}
            if user_id not in self._graph:
                return inferred
                
            # Find owned devices
            owned_devices = [
                dst for _, dst, d in self._graph.out_edges(user_id, data=True)
                if d.get("rel") == "owns"
            ]
            
            # Find rooms those devices are located in
            for dev in owned_devices:
                for _, dst, d in self._graph.out_edges(dev, data=True):
                    if d.get("rel") == "located_in":
                        if self._graph.nodes[dst].get("type") == "room":
                            inferred["near_rooms"].append(dst)
                            
                # Check for recent events triggered by this device
                for src, _, d in self._graph.in_edges(dev, data=True):
                    if d.get("rel") == "triggered":
                        if self._graph.nodes[src].get("type") == "event":
                            inferred["active_devices"].append(dev)
                            break
                            
            inferred["near_rooms"] = list(set(inferred["near_rooms"]))
            inferred["active_devices"] = list(set(inferred["active_devices"]))
            return inferred

