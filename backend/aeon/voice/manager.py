"""
aeon/voice/manager.py — Conversation Orchestrator

Handles natural language text inputs, maintains conversation memory,
routes queries to the Knowledge Graph, executes commands via the Policy Engine,
and generates natural language insights.
"""

from __future__ import annotations

import structlog
import re
from typing import Any
from collections import deque
from datetime import datetime, timezone

log = structlog.get_logger(__name__)


class ConversationManager:
    """
    Manages the conversational state and routes text intents.
    """

    def __init__(self, graph: Any, policy: Any, memory_store: Any, max_history: int = 5):
        self._graph = graph
        self._policy = policy
        self._store = memory_store
        self._ws_bus: Any = None       # injected after construction

        # In-memory context
        self._history: deque[dict[str, str]] = deque(maxlen=max_history)

        # Naive intent patterns for edge execution (no LLM required)
        # Order matters — more specific patterns first
        self._patterns = {
            "FEEDBACK": re.compile(
                r"\b(false[.\s]alarm|no,?\s*(that|it)\s+was|wrong|don.t|mistake)\b",
                re.IGNORECASE,
            ),
            "SENSOR_QUERY": re.compile(
                r"\b(what|how).*(temperature|humidity|hot|cold|warm)\b", re.IGNORECASE
            ),
            "MOTION_QUERY": re.compile(
                r"\b(motion|movement|detected|person|someone)\b", re.IGNORECASE
            ),
            "STATUS_QUERY": re.compile(
                r"\b(status|state|connected|arduino|model|version|npu|loaded)\b",
                re.IGNORECASE,
            ),
            "ALERT_QUERY": re.compile(
                r"\b(alert|alarm|trigger|anomaly|today)\b", re.IGNORECASE
            ),
            "COMMAND": re.compile(r"\b(turn|switch)\b.*\b(on|off)\b", re.IGNORECASE),
            "GRAPH_QUERY": re.compile(r"\b(where|who).*(is|are)\b", re.IGNORECASE),
        }

    def attach_bus(self, ws_bus: Any) -> None:
        self._ws_bus = ws_bus

    async def process_text(self, text: str) -> str:
        """Called from WS bus — process and publish voice_status updates."""
        if self._ws_bus:
            await self._ws_bus.publish("voice_status", {
                "state": "processing",
                "last_query": text,
            })
        response = await self.handle_utterance(text)
        if self._ws_bus:
            await self._ws_bus.publish("voice_status", {
                "state": "idle",
                "last_query": text,
                "last_response": response,
            })
        return response

    async def handle_utterance(self, text: str, user_id: str = "default_user") -> str:
        """Process a text command and return the synthesized text response."""
        if not text or not text.strip():
            return "I didn't quite catch that."

        text = text.strip()
        self._history.append({"role": "user", "text": text})
        log.info("voice.utterance_received", text=text, user_id=user_id)

        intent = self._classify_intent(text)
        context = await self._graph.infer_context(user_id)

        response = ""
        try:
            if intent == "SENSOR_QUERY":
                response = await self._handle_sensor_query(text, context)
            elif intent == "MOTION_QUERY":
                response = await self._handle_motion_query(context)
            elif intent == "STATUS_QUERY":
                response = await self._handle_status_query(text)
            elif intent == "ALERT_QUERY":
                response = await self._handle_alert_query(text)
            elif intent == "COMMAND":
                response = await self._handle_command(text, context)
            elif intent == "GRAPH_QUERY":
                response = await self._handle_graph_query(text, context)
            elif intent == "FEEDBACK":
                response = await self._handle_feedback(text, context)
            else:
                response = (
                    "I heard you, but I'm not sure how to help with that yet. "
                    "Try asking about temperature, motion, system status, or alerts."
                )
        except Exception:
            log.exception("voice.handling_error")
            response = "Sorry, I encountered an error while processing that."

        self._history.append({"role": "assistant", "text": response})
        return response

    def _classify_intent(self, text: str) -> str:
        for intent, pattern in self._patterns.items():
            if pattern.search(text):
                return intent
        return "UNKNOWN"

    async def _handle_sensor_query(self, text: str, context: dict) -> str:
        history = await self._store.get_sensor_history(minutes=2)
        if not history:
            return "I don't have any recent sensor data. The Arduino may be disconnected."

        latest = history[-1]
        temp = latest.get("temperature", 0.0)
        hum = latest.get("humidity", 0.0)

        room_str = "the room"
        if context.get("near_rooms"):
            room_str = f"the {context['near_rooms'][0]}"

        return (
            f"The temperature in {room_str} is {temp:.1f} degrees Celsius, "
            f"with {hum:.1f} percent relative humidity."
        )

    async def _handle_motion_query(self, context: dict) -> str:
        history = await self._store.get_sensor_history(minutes=2)
        if not history:
            return "No recent sensor data available."

        latest = history[-1]
        motion = latest.get("motion", False)
        ts_str = latest.get("ts", "")
        try:
            ts = datetime.fromisoformat(ts_str)
            time_ago = (
                datetime.now(tz=timezone.utc) - ts.replace(tzinfo=timezone.utc)
            ).seconds
            time_str = f"{time_ago} seconds ago"
        except (ValueError, TypeError):
            time_str = "recently"

        if motion:
            return f"Yes, motion was detected {time_str}."
        return f"No motion detected as of {time_str}."

    async def _handle_status_query(self, text: str) -> str:
        events = await self._store.get_recent_events(limit=10)
        sys_events = [
            e for e in events
            if e.get("category") in ("SERIAL", "MODEL", "SYSTEM", "DREAM_STATE")
        ]
        if sys_events:
            last = sys_events[0]
            return (
                f"Last system event: {last.get('name', 'unknown')} "
                f"at {last.get('ts', 'unknown')}."
            )
        return "All systems appear nominal. No recent system events recorded."

    async def _handle_alert_query(self, text: str) -> str:
        events = await self._store.get_recent_events(limit=20)
        alerts = [e for e in events if e.get("category") == "ANOMALY"]
        false_alarms = [e for e in events if e.get("name") == "false_alarm"]
        if not alerts:
            return "No anomaly alerts have been recorded recently."
        return (
            f"There have been {len(alerts)} anomaly events, "
            f"of which {len(false_alarms)} were marked as false alarms."
        )

    async def _handle_command(self, text: str, context: dict) -> str:
        action = "on" if "on" in text.lower() else "off"
        target = "fan"
        if "light" in text.lower():
            target = "light"
        elif "relay" in text.lower():
            target = "relay"

        success = await self._policy.execute_override(target, action)
        if success:
            return f"Okay, turning {action} the {target}."
        return f"I couldn't turn {action} the {target} right now."

    async def _handle_graph_query(self, text: str, context: dict) -> str:
        if "phone" in text.lower() or "device" in text.lower():
            if context.get("near_rooms"):
                return f"I think your device is near the {context['near_rooms'][0]}."
            return "I'm not sure where your device is right now."
        return "I can only answer questions about registered devices and rooms."

    async def _handle_feedback(self, text: str, context: dict) -> str:
        """
        Handle user feedback — logs a USER_CORRECTION event to persistent storage
        so Dream State can consolidate it.
        """
        try:
            await self._store.log_event(
                "USER_CORRECTION",
                "voice_feedback",
                {"text": text, "context": context},
            )
            log.info("voice.feedback_logged", text=text)
        except Exception:
            log.exception("voice.feedback_log_error")
        return "Thanks for the feedback. I'll adjust my behaviour next time."

    def get_history(self) -> list[dict[str, str]]:
        return list(self._history)
