# Activity Engine Documentation

The Activity Engine translates environmental and temporal context states into semantic user activities (e.g. Working, Sleeping, Away).

---

## 1. Inference Pipeline

The engine continuously evaluates context dimensions against a heuristic classifier ruleset:

1. **Sleeping**: Inferred when motion is absent and temporal hour is late night ($22\text{:00} - 06\text{:00}$).
2. **Away**: Inferred when motion is absent during daytime or evening, indicating vacant premises.
3. **Working**: Inferred when motion is present during weekday daytime hours ($08\text{:00} - 17\text{:00}$).
4. **Watching TV**: Inferred when motion is present during evening hours ($17\text{:00} - 22\text{:00}$).
5. **Cooking**: Inferred when motion is present around lunch or dinner times.
6. **Relaxing**: Inferred when motion is present during off-hours/weekends.
7. **Idle**: Default fallback when no specific activity patterns match.

---

## 2. Activity Confidence & Stability

Every activity output includes metadata representing its quality:

- **Confidence**: A probability score $\in [0.0, 1.0]$ based on condition matches.
- **Supporting Evidence**: Key conditions that triggered the activity (e.g., `"motion": True`).
- **Prediction Stability**: A metric tracking prediction continuity. Stability is high ($1.0$) if consecutive frames yield the same activity and lower if confidence fluctuates.
- **Trend**: Positive/negative change in confidence over time.

---

## 3. Rolling Transition History

To prevent rapid oscillation and build routine models, the Activity Engine logs transitions into a rolling history of 50 items:

- **Start Time / End Time**: ISO-8601 timestamps of the activity duration.
- **Transition Reason**: Reason for activity change (e.g., `switched_to_Sleeping`).
- **Duration**: Total time elapsed in seconds.
- **Confidence Trend**: Rolling average confidence variation.
