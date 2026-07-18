# Dream State Documentation

The Dream State is a background processing mode designed for the Arduino UNO Q and backend systems to consolidate memory and optimize policy parameters during periods of low activity.

---

## 1. Scheduling & Eligibility

Dream State is not a low-power sleep mode. It runs as a scheduled background task and is only eligible when the following criteria are met:
- **Idle Timeout**: The system has been idle (no incoming user commands or sensor overrides) for at least 10 seconds.
- **No Deployment**: No active model or firmware deployment is running.
- **Empty Queues**: Inbound communication buffers are empty.

### Interruption
If a new user action (manual switch, button press, serial payload) occurs while dreaming, the state is immediately interrupted via `DreamState::interrupt(reason)`, logging the duration and resuming active control within milliseconds to assure no automation delays.

---

## 2. Background Optimization

During Dream State, the firmware performs the following optimization phases:
1. **Memory Consolidation**: Merges duplicate observations and removes obsolete transient items.
2. **Confidence Tuning**: Boosts model and policy confidence ratings slightly if no errors occurred during the active session.
3. **Weight Calibration**: Updates reasoning weights for comfort and automation rules based on active history.

---

## 3. Telemetry

Dream lifecycle events are communicated to the Snapdragon PC using specific protocol messages:
- `DreamStarted`: Alerts the backend that background optimization is running.
- `DreamCompleted`: Flushes details of consolidated memory counts and run duration.
- `DreamInterrupted`: Signals that user activity interrupted the dream cycle.
