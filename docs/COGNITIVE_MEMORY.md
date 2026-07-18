# Cognitive Memory Subsystem Documentation

The Cognitive Memory subsystem manages persistent and semi-persistent remembered knowledge, avoiding temporary variables to focus on long-term behavioral and environmental insights.

---

## 1. Memory Model & Categories

Cognitive Memory divides observations into eight distinct logical categories:
- **Preference Memory**: User comfort corrections and adaptations.
- **Decision Memory**: Logs of executed decisions alongside their alternative choices and winning scores.
- **Context Memory**: Historic sensor context maps.
- **Activity Memory**: Frequencies and durations of inferred user activities.
- **Device Memory**: Statistics on latencies, commands, and communication signals.
- **Policy Memory**: Historic policy activation schedules.
- **Inference Memory**: Accuracy rates and confidence outputs of models.
- **Interaction Memory**: Dialogs and feedback from user interface endpoints.

---

## 2. Retention and Garbage Collection

To manage memory capacity and keep observations fresh, Cognitive Memory implements a category-level retention policy:
- **Capacity limits**: Category instances support a maximum entries size (e.g. 100 entries). When exceeded, the oldest items are automatically dropped (FIFO).
- **Age pruning**: Prunes entries older than a configurable maximum age duration (default 7 days).
- **Protected memories**: Certain crucial historical observations can be marked to bypass standard GC.

---

## 3. Retrieval

Memory retrieval supports clean querying by matching context parameters (e.g. retrieve memories matching `"activity": "Working"`). This feeds historical baseline parameters back to the Context and Reasoning engines during decision ticks.
