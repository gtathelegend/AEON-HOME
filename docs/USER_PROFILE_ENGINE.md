# User Profile Engine Documentation

The User Profile Engine manages user-specific automation preferences and tracks behavioral adaptation signals over time.

---

## 1. Profile Model & Structure

Instead of static setting attributes, every user preference is modeled with adaptive metadata:

```json
{
  "preferred_temperature": {
    "current_value": 21.0,
    "confidence": 1.0,
    "source": "system_default",
    "last_modified": "2026-07-19T00:50:00Z",
    "manual_count": 0,
    "automatic_count": 0,
    "learning_weight": 1.0,
    "history_size": 0
  }
}
```

- **Current Value**: The active setting value (e.g. comfort temperature).
- **Confidence**: Multi-factor confidence index $\in [0.1, 1.0]$ representing setting stability. Overrides decrease confidence; continuous compliance builds it.
- **Manual Count / Automatic Count**: Tracks manual user overrides vs automatic system activations.
- **Learning Weight**: Degree of susceptibility to updates.

---

## 2. Learning Signals

The engine intercepts user behavior actions to accumulate learning signals:

1. **Repeated Temperature Corrections**: Fired on voice temperature requests or thermostat dials.
2. **Lighting/Actuator Changes**: Captured on relay toggle commands.
3. **Manual Overrides**: Logged on false alarm button presses or command overrides.

*Note: This commit compiles and records learning signal metadata but does not yet perform autonomous optimization routines (reserved for future commits).*

---

## 3. Persistence

Profiles are saved and loaded directly from the unified **Knowledge Graph** database:
- Each user preference is stored as a node in the graph: `pref:{user_id}:{setting}`.
- Attributes on the preference node contain the complete adaptive metadata dictionary.
- A directed edge of type `prefers` links the user node to the preference node.
- Selected user profile version is also replicated to the firmware's `AeonState` to maintain local consistency during reboots.
