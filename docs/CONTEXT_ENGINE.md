# Context Engine Documentation

The Context Engine is responsible for building a unified, read-only representation of the environmental, temporal, device, system, and user conditions of the home. 

---

## 1. Architecture & Design

The Context Engine follows a decoupled provider-aggregator design. It gathers individual context dimensions via provider classes and aggregates them into a single frozen snapshot.

```
                  ┌───────────────────────┐
                  │ TimeContextProvider   ├────────┐
                  └───────────────────────┘        │
                  ┌───────────────────────┐        │
                  │ SensorContextProvider ├──────┐ │
                  └───────────────────────┘      │ │
                  ┌───────────────────────┐      ▼ ▼
                  │ DeviceContextProvider ├─► Aggregator ──► ImmutableContext
                  └───────────────────────┘      ▲ ▲
                  ┌───────────────────────┐      │ │
                  │ UserContextProvider   ├──────┘ │
                  └───────────────────────┘        │
                  ┌───────────────────────┐        │
                  │ SystemContextProvider ├────────┘
                  └───────────────────────┘
```

---

## 2. Context Providers

Context features are grouped into categories:

1. **Environmental Context**: Live sensor feeds (temperature, humidity, motion, mean temperature, temperature variance, and motion delta).
2. **Temporal Context**: System time features (ISO timestamp, hour, minute, day of week, and weekend status flag).
3. **Device Context**: Serial connection status, COM port location, active relay outputs, and registered devices count.
4. **User Context**: Active user identifier and authorized user lists.
5. **System Context**: Snapdragon PC uptime and host network state.
6. **Runtime Context**: Model statistics (active model version, inference average confidence, error rate).
7. **Behavioral Context**: Tracks rolling manual override history.

Dynamic registration is supported via `ContextEngine.register_provider(category, provider)` to allow adding new providers without code modifications.

---

## 3. Aggregation Lifecycle

Every context update executes a deterministic 6-stage lifecycle:

```
Collect ──► Normalize ──► Merge ──► Validate ──► Freeze ──► Publish
```

1. **Collect**: Queries all registered context providers concurrently.
2. **Normalize**: Fits raw provider payloads into consistent types and schema.
3. **Merge**: Combines raw maps and merges manual overrides.
4. **Validate**: Assures values remain within physical limits (e.g. clamps temperature to $[-40.0, 85.0]$ and humidity to $[0.0, 100.0]$).
5. **Freeze**: Locks the structure into a read-only, frozen `ImmutableContext` instance.
6. **Publish**: Broadcasts the unified context across the WebSocket bus to clients.
