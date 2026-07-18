# Policy Engine Documentation

The Policy Engine implements a deterministic conflict-resolution evaluation pipeline that translates user profile preferences, inferred semantic activities, and sensor context into actuation decisions.

---

## 1. Evaluation Pipeline

The evaluation pipeline executes in seven distinct stages on every incoming feature frame:

```
Collect Policies ──► Validate ──► Rank ──► Evaluate ──► Resolve Conflicts ──► Produce Decision ──► Publish
```

1. **Collect Policies**: Fetches all registered policy objects currently in the active set.
2. **Validate**: Verifies each policy is initialized and meets basic safety constraints.
3. **Rank**: Orders the active policy set by priority levels in descending order.
4. **Evaluate**: Executes policy conditionals concurrently or sequentially.
5. **Resolve Conflicts**: The highest-ranking policy that evaluates to a non-null payload wins the evaluation.
6. **Produce Decision**: Packs the outcome into a standardized `Decision` object.
7. **Publish**: Distributes the decision across WebSocket to client apps and acts as the actuator source.

---

## 2. Policy Priorities

System policies are organized into eight priority levels:

| Level | Priority Category | Description / Policy Example |
| :---: | :--- | :--- |
| **8** | **Emergency** | Life-safety rules (e.g., thermal thresholds > 50°C). |
| **7** | **Safety** | Equipment and freeze protection rules. |
| **6** | **Security** | Intruders, sensor state mismatch while Away. |
| **5** | **User Override** | Voice assistant commands and dashboard button clicks. |
| **4** | **Comfort** | Climate rules matching active profile settings. |
| **3** | **Automation** | Rules implied by Knowledge Graph schemas. |
| **2** | **Optimization** | Eco-friendly energy conservation schedules. |
| **1** | **Background** | Nominal system fallbacks. |

---

## 3. Conflict Resolution

Because multiple policies can trigger at once, conflicts are resolved deterministically:
- **Priority Dominance**: Policies are evaluated in descending priority order. An Emergency policy (8) always takes precedence over an Optimization policy (2).
- **User Override vs Automation**: If a user issues a manual command, the `UserOverridePolicy` (5) overrides graph-implied `AutomationPolicy` rules (3) or `Eco-saving` routines (2), allowing manual control.
- **Traceability**: The resulting Decision object contains a `conflict_log` detailing which policies were evaluated and rejected, recording the exact reason why the winning policy was selected.
