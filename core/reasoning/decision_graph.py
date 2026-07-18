# core/reasoning/decision_graph.py

from __future__ import annotations

import networkx as nx
from typing import Any, Dict, List


class DecisionGraph:
    """
    DAG representing reasoning influences on decisions.
    Nodes represent context variables, user preferences, activity inferences,
    and policy outputs. Edges represent influence paths.
    """

    def __init__(self) -> None:
        self._graph = nx.DiGraph()

    def build_graph(
        self,
        context: Dict[str, Any],
        activity: Dict[str, Any],
        profile: Dict[str, Any],
        policies: List[Any],
        model_output: Dict[str, Any],
        device_caps: Dict[str, Any],
    ) -> None:
        """Dynamically construct nodes and edges representing the reasoning map."""
        self._graph.clear()

        # ── 1. Add Context Nodes ──
        env = context.get("environmental", {})
        temp = env.get("temperature", 21.0)
        motion = env.get("motion", False)
        self._graph.add_node("context:temperature", type="context", value=temp, weight=1.0)
        self._graph.add_node("context:motion", type="context", value=motion, weight=1.0)

        # ── 2. Add Activity Node ──
        act_name = activity.get("activity", "Idle")
        act_conf = activity.get("confidence", 0.5)
        self._graph.add_node(f"activity:{act_name}", type="activity", confidence=act_conf)
        
        # Link context to activity
        self._graph.add_edge("context:motion", f"activity:{act_name}", relation="triggers")

        # ── 3. Add Model Output Nodes ──
        presence_prob = model_output.get("presence_prob", 0.0)
        self._graph.add_node("model:presence_prob", type="model_output", value=presence_prob)

        # ── 4. Add User Preferences Nodes ──
        pref_temp = profile.get("preferences", {}).get("preferred_temperature", {}).get("current_value", 21.0)
        pref_conf = profile.get("preferences", {}).get("preferred_temperature", {}).get("confidence", 1.0)
        self._graph.add_node("preference:temperature", type="user_preference", value=pref_temp, confidence=pref_conf)

        # ── 5. Add Policies Nodes ──
        for p in policies:
            self._graph.add_node(f"policy:{p.identifier}", type="policy", priority=p.priority)
            
            # Establish influence relationships
            if p.identifier == "comfort_policy":
                self._graph.add_edge("context:temperature", f"policy:{p.identifier}", relation="influences")
                self._graph.add_edge("preference:temperature", f"policy:{p.identifier}", relation="influences")
            elif p.identifier == "security_policy":
                self._graph.add_edge(f"activity:{act_name}", f"policy:{p.identifier}", relation="influences")
                self._graph.add_edge("context:motion", f"policy:{p.identifier}", relation="influences")
            elif p.identifier == "automation_policy":
                self._graph.add_edge("model:presence_prob", f"policy:{p.identifier}", relation="influences")

        # ── 6. Add Device Capabilities Nodes ──
        for cap, supported in device_caps.items():
            if supported:
                self._graph.add_node(f"capability:{cap}", type="device_capability")

    def get_influences(self, target_node: str) -> List[Dict[str, Any]]:
        """Return all nodes that directly influence the target node."""
        influences = []
        if target_node in self._graph:
            for src in self._graph.predecessors(target_node):
                influences.append({
                    "node": src,
                    "attributes": dict(self._graph.nodes[src]),
                    "relation": self._graph.edges[src, target_node].get("relation", "influences"),
                })
        return influences

    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to node-link format for API visualization."""
        return nx.node_link_data(self._graph)
