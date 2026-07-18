# Testing Guide — Framework & Integration

This document outlines the testing strategy, test layers, and commands for validating the security, persistence, and intelligence layers of ÆON Home.

---

## 1. Test Organization

Tests are grouped under the `tests/` directory:

| Suite / Layer | Target Validation | Tool |
| :--- | :--- | :--- |
| **Unit Tests** | Math helper functions, token expirations, state layouts. | pytest |
| **Integration Tests** | WebSocket gateways, event routing, database write integrity. | pytest |
| **Cognitive Verification** | Reasoning outcomes, Alternative action lists, Explanations. | pytest |
| **Firmware Tests** | EEPROM checkpoint loading, command callbacks. | Unity C / Mock |

---

## 2. Running Test Suites

### Complete System Integration Run
To run all 53 integration tests validating endpoints, tokens, model deployments, and policy calculations:
```bash
cd backend
source .venv/bin/activate
pytest ../tests -v --tb=short
```

---

## 3. Mocking Hardware / Comm Ports

For testing without a physical Arduino Uno Q connected:
- **`AEON_DEMO_MODE=true`**: Enables simulated telemetry feed in the backend.
- **`DummyBridge`**: Mocks the serial port writer connection pool so all REST endpoints execute without throwing connection errors.
