# Developer Guide — How to Extend ÆON Home

This guide walks you through standard procedures for expanding the capabilities of the ÆON Home edge platform.

---

## 1. Adding a New Device or Capability

1. **Backend Registry Update**:
   Update `core/registry/devices.py` or invoke the REST API payload to register the new device ID, device type, capabilities list, and communication baseline.
2. **Knowledge Graph Node**:
   Add the corresponding relationship edge in the local SQLite graph db to associate the device with home zones or specific activities.

---

## 2. Adding a New Policy or Rule

1. **Policy Class Creation**:
   Implement a new class inheriting from `BasePolicy` in `core/policy/policies.py` or equivalent:
   ```python
   class ClimateComfortPolicy(BasePolicy):
       def evaluate(self, context: ContextState, profile: UserProfile) -> PolicyResponse:
           # return policy outcome (ON, OFF, or UNCHANGED)
   ```
2. **Engine Registration**:
   Append your policy class instance to the evaluation chain in the `PolicyEngine` initialization within `backend/aeon/main.py`.

---

## 3. Adding a New API Endpoint

1. **Route Mapping**:
   Create or edit the relevant router module in `backend/aeon/api/routes/` (e.g. `cognitive_api.py` or a new file).
2. **App Injection**:
   Include the new router in `create_app` inside `backend/aeon/api/app.py` mapping to `/api/v1`.
3. **Shared Type contracts**:
   Verify any new response payload mirrors schemas in `shared/types/models.py`.

---

## 4. Adding a New Protocol Message

1. **Firmware Signature**:
   Declare the transmission function signature in [aeon_protocol.h](file:///c:/Users/vedaa/OneDrive/Documents/ÆON/Snapdragon%20Multiverse%20Hackathon/AEON-Home/AEON-HOME/firmware/firmware/sentinel/protocols/aeon_protocol.h) and implement its serialization block inside [aeon_protocol.cpp](file:///c:/Users/vedaa/OneDrive/Documents/ÆON/Snapdragon%20Multiverse%20Hackathon/AEON-Home/AEON-HOME/firmware/firmware/sentinel/protocols/aeon_protocol.cpp).
2. **Gateway Router**:
   Extend `CommunicationGateway::handle_incoming` inside `backend/aeon/services/communication_gateway.py` to route the packet to your target application service.
