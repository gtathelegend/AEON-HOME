# Recommendation Engine Documentation

The Recommendation Engine identifies routines and provides optimization suggestions to the user without executing them automatically, prioritizing safety.

---

## 1. Habit Discovery

By analyzing long-term experience memory (e.g. repeated time-based manual switches), the system identifies recurring user schedules:
- **Morning/Bedtime routines**: Preferred climate settings during specific hours.
- **Work schedules**: Automated lighting/power savings when inferred activity is "Away" or "Working".
- **Weekend behaviors**: Comfortable temperature baselines.

---

## 2. Suggestion Generation

Discovered habits are formulated as explainable recommendations:
- **Suggested Preference Shifts**: E.g. "We noticed you dial temp to 24°C on weekdays. Update preferred temperature to 24°C?"
- **Suggested Schedules**: Energy optimization dimming periods.
- **Suggested Device Grouping**: Bundling multiple lights/switches.

---

## 3. Human-in-the-Loop & Safety

All recommendations are subject to safety constraints:
- **No Auto-execution**: Suggestions must be explicitly approved via user confirmation before applying.
- **Safety Priority**: Safety policies, emergency thermal thresholds, and security parameters can never be overridden or disabled by recommendation approval.
