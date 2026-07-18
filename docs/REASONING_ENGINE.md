# Reasoning Engine Documentation

The Reasoning Engine is the central brain of the cognitive intelligence layer, evaluating competing decisions, ranking alternative actions, gathering evidence items, and producing structured final decision objects.

---

## 1. Decision Graph (DAG)

Reasoning influences are represented internally using a Directed Acyclic Graph (DAG) using NetworkX:
- **Nodes**: Context variables (temperatures, motion sensors), user comfort preferences, inferred user activities, QNN model prediction probabilities, active policy objects, and device capabilities.
- **Edges**: Represent relationships and information influence flows. For example, `context:motion` $\rightarrow$ `activity:Working` represents trigger relationships, and user preference values influence climate policy nodes.

---

## 2. Evidence Collection

For every decision executed, the Reasoning Engine collects supporting evidence items with the following structure:
- **Source**: Origin of information (e.g. `environmental_sensors`, `user_override`, `comfort_deviation`).
- **Timestamp**: ISO UTC time when the evidence was collected.
- **Weight**: Relative importance of the evidence.
- **Confidence / Reliability**: Precision of sensor readings or user feedback.

---

## 3. Alternative Decision Ranking

The engine evaluates five potential actions:
1. **ON**: Turn light/relay on.
2. **OFF**: Turn light/relay off.
3. **Unchanged**: Do not alter device state.
4. **Delay Action**: Postpone execution.
5. **Notify User**: Play beep/alert buzzer.

Each alternative receives a composite score calculated using:
$$Score = W_p \cdot \text{Priority} + W_c \cdot \text{Confidence} + W_r \cdot \text{Reliability} + W_e \cdot \text{EvidenceCoverage}$$
Where priority refers to the policy priority level (8 down to 1), confidence refers to the base action confidence, reliability is the device history metrics, and coverage is the count of supporting evidence items.
The alternative with the highest score is selected as the winning decision action.
