# Device Registry Documentation

The Enhanced Device Registry acts as the central authority for every connected device on the local network, tracking capabilities, health status, and reliability.

---

## 1. Device Capability Model

Capabilities are explicitly defined for each registered device, avoiding ad-hoc features check logic:
- **`sensors`**: Temperature, humidity, or motion sensor arrays.
- **`climate`**: HVAC, heater, or cooling actuator interfaces.
- **`lighting`**: Dimmers, relays, or smart bulb modules.
- **`notifications`**: Beep buzzers, alarms, or email triggers.
- **`switches`**: Power relays, smart outlets.

---

## 2. Health & Reliability Metrics

The registry tracks runtime health metrics by intercepting command completions:
- **Health State**: Classified as `healthy`, `warning`, or `critical` based on reliability.
- **Reliability Index**: Float value $\in [0.0, 1.0]$ representing command execution success rates.
- **Average Response Time**: Exponential Moving Average (EMA) of response latencies in milliseconds.
- **Communication Quality**: Signal quality factor representing packet drops.

---

## 3. Context & Activity Associations

Devices maintain associations with contexts and activities:
- **Associated Contexts**: Physical locations or environments where the device is active (e.g. `home`, `office`).
- **Associated Activities**: Activities that trigger device usage (e.g. `Working`, `Sleeping`).
- **Device Confidence**: Weighting representing overall device usability.
