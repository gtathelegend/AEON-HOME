# Explainability Engine Documentation

The Explainability Engine translates internal, abstract reasoning details, conflict resolutions, and confidence statistics into human-readable explanation objects.

---

## 1. Explanation Pipeline

On every reasoning tick, the Explainability Engine runs the following pipeline:
1. **Extract decision parameters**: Evaluates the winning policy, alternatives, and context.
2. **Resolve Reason Codes**: Maps conditions to stable reason codes.
3. **Draft summaries**: Constructs clean, human-readable descriptions of why the action was taken and what evidence was used.
4. **Compile Rejected Policies**: Explains why candidate actions from other policies were overridden or rejected.
5. **Pack Explanation Object**: Returns a structured `ExplanationModel` ready for transmission.

---

## 2. Standardized Reason Codes

To assure stability and compatibility across versions, the engine classifies decisions into eight standardized codes:
- **`MANUAL_OVERRIDE`**: The user manually requested this command (e.g. voice control).
- **`USER_PREFERENCE`**: Action satisfies comfort preferences of the active user profile.
- **`HIGH_CONFIDENCE_ACTIVITY`**: Inferred user activity is highly stable and triggers automation.
- **`LOW_MODEL_CONFIDENCE`**: On-device model confidence fell below safety limits, requiring policy fallback.
- **`ENERGY_OPTIMIZATION`**: Action prioritizes power savings.
- **`DEVICE_UNAVAILABLE`**: A preferred device is offline, triggering fallback routing.
- **`TIME_BASED`**: Action scheduled by time-of-day constraints.
- **`POLICY_PRIORITY`**: Evaluated due to safety/emergency rule precedence.

---

## 3. Confidence Breakdown

Instead of exposing one generic confidence value, the explanation contains a granular breakdown:
- **Context Confidence**: Accuracy quality of sensor streams.
- **Activity Confidence**: Classifier confidence in inferred user routines.
- **Policy Confidence**: Comfort preference weight/confidence.
- **Model Confidence**: Probability output from the QNN models.
- **Reasoning Confidence**: Evaluation spread metric indicating spread between alternatives.
- **Overall Confidence**: Mathematical average/composite representing total decision quality.
