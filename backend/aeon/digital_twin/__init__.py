"""
aeon/digital_twin/__init__.py

Digital Twin engine for ÆON Home.

Exports the ContextEngine and appliance twin classes:
  ContextEngine   — aggregates sensor telemetry into a room-context state
  SmartACTwin     — adaptive air conditioning model
  SmartLightTwin  — adaptive lighting model
  RobotVacuumTwin — robot vacuum state and path model
"""

from .context_engine import ContextEngine
from .appliances import SmartACTwin, SmartLightTwin, RobotVacuumTwin

__all__ = [
    "ContextEngine",
    "SmartACTwin",
    "SmartLightTwin",
    "RobotVacuumTwin",
]
