# Learning Engine Documentation

The Learning Engine is responsible for executing the on-device feedback loop, evaluating policy choices, and adapting comfort preferences based on user behavior.

---

## 1. Feedback Pipeline & Classification

Feedback events originate from voice control overrides, dashboard toggles, or physical button interactions. The engine classifies feedback into:
- **`positive`**: Compliance with automation rules.
- **`negative`**: User rejection or cancellation.
- **`correction`**: User adjustments immediately following an automation decision.
- **`preference_change`**: Setting values updated explicitly by the user.
- **`policy_conflict`**: Contradictory rules triggering concurrently.

---

## 2. Adaptation Lifecycle

Instead of overreacting to individual overrides, the Learning Engine applies conservative adjustments:
1. **Track corrections**: Increments a counter for consecutive overrides (`consecutive_corrections`).
2. **Preference Shifts**: Only updates comfort parameters (such as `preferred_temp` in `AeonState`) after 3 consecutive corrections.
3. **Weight Decays**: Slowly reduces policy evaluation weights if overrides occur frequently, letting alternate policies take precedence.
4. **Restoration**: Gradually builds weights back to 1.0 when automations are completed successfully without user intervention.

---

## 3. Local Evaluation

The engine never trains neural networks locally. It evaluates decisions and calculates EMA averages of:
- Prediction confidence.
- Execution latencies.
- Rule compliance rates.
These statistics are flushed to the Snapdragon PC to construct lifelong retraining datasets.
