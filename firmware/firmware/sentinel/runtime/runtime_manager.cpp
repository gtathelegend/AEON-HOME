/**
 * runtime_manager.cpp — Main system coordinator implementation.
 */
#include "runtime_manager.h"
#include <ArduinoJson.h>

// ── Router Callback Wrapper ──────────────────────────────────────────────────
static void routerCallback(const char* typ, const char* json_str, void* context) {
    RuntimeManager* mgr = static_cast<RuntimeManager*>(context);
    if (!mgr) return;

    if (strcmp(typ, "policy_update") == 0) {
        mgr->handlePolicyUpdate(json_str);
    } else if (strcmp(typ, "model_update") == 0) {
        mgr->handleModelUpdate(json_str);
    } else if (strcmp(typ, "relay_set") == 0) {
        mgr->handleRelaySet(json_str);
    } else if (strcmp(typ, "buzzer") == 0) {
        mgr->handleBuzzer(json_str);
    } else if (strcmp(typ, "checkpoint") == 0) {
        mgr->handleCheckpoint(json_str);
    }
}

// ── Constructor ──────────────────────────────────────────────────────────────
RuntimeManager::RuntimeManager()
    : _checkpoint(_storage),
      _protocol(_transport),
      _telemetry(_sensors, _features, _protocol),
      _local_policy(_actuators, _protocol),
      _health(_transport) {}

// ── Main Tick ────────────────────────────────────────────────────────────────
void RuntimeManager::tick() {
    // 1. Keep WiFi and WebSocket alive
    _transport.tick();

    // 2. Read inbound buffer from transport and route commands
    char rx_buf[MAX_CMD_PAYLOAD];
    int len = _transport.receive(rx_buf, sizeof(rx_buf));
    if (len > 0) {
        _router.route(rx_buf);
    }

    // 3. Process periodic tasks
    _scheduler.tick();
}

// ── Boot Pipeline ────────────────────────────────────────────────────────────
bool RuntimeManager::boot() {
    Serial.println("[BOOT] Starting deterministic 13-stage boot pipeline...");

    if (!stage01_hardware_init()) return false;
    if (!stage02_storage_init()) return false;
    if (!stage03_config_load()) return false;
    if (!stage04_checkpoint_recover()) return false;
    if (!stage05_wifi_init()) return false;
    if (!stage06_transport_init()) return false;
    if (!stage07_device_registry_init()) return false;
    if (!stage08_model_load()) return false;
    if (!stage09_policy_init()) return false;
    if (!stage10_scheduler_init()) return false;
    if (!stage11_telemetry_init()) return false;
    if (!stage12_security_init()) return false;
    if (!stage13_runtime_ready()) return false;

    return true;
}

bool RuntimeManager::stage01_hardware_init() {
    _sensors.init();
    _actuators.init();
    Serial.println("[BOOT] Stage 1: Hardware Init [OK]");
    return true;
}

bool RuntimeManager::stage02_storage_init() {
    _storage.init();
    Serial.println("[BOOT] Stage 2: Storage Init [OK]");
    return true;
}

bool RuntimeManager::stage03_config_load() {
    // Configuration constants are loaded from runtime_config.h.
    Serial.println("[BOOT] Stage 3: Configuration Load [OK]");
    return true;
}

bool RuntimeManager::stage04_checkpoint_recover() {
    bool recovered = _checkpoint.restore(&_state);
    if (recovered) {
        Serial.print("[BOOT] Stage 4: Checkpoint Recovered [OK] Model V: ");
        Serial.println(_state.model_v);
    } else {
        _checkpoint.reset(&_state);
        Serial.println("[BOOT] Stage 4: Checkpoint Recover Failed. Defaults Loaded.");
    }
    return true;
}

bool RuntimeManager::stage05_wifi_init() {
    // connect() connects to WiFi and initializes WebSocketsClient
    bool ok = _transport.connect();
    if (ok) {
        Serial.println("[BOOT] Stage 5: WiFi association [OK]");
    } else {
        Serial.println("[BOOT] Stage 5: WiFi association [FAIL]");
    }
    return true;
}

bool RuntimeManager::stage06_transport_init() {
    // WebSocket registration message sent after connect
    Serial.println("[BOOT] Stage 6: Transport Initialization [OK]");
    return true;
}

bool RuntimeManager::stage07_device_registry_init() {
    _device_registry.init();
    Serial.println("[BOOT] Stage 7: Device Registry Initialized [OK]");
    return true;
}

bool RuntimeManager::stage08_model_load() {
    _model_runtime.init();
    Serial.println("[BOOT] Stage 8: Model Loading [OK]");
    return true;
}

bool RuntimeManager::stage09_policy_init() {
    _local_policy.init();

    // Register router command callbacks
    _router.registerHandler("policy_update", routerCallback, this);
    _router.registerHandler("model_update", routerCallback, this);
    _router.registerHandler("relay_set", routerCallback, this);
    _router.registerHandler("buzzer", routerCallback, this);
    _router.registerHandler("checkpoint", routerCallback, this);

    Serial.println("[BOOT] Stage 9: Policy Engine Initialized [OK]");
    return true;
}

bool RuntimeManager::stage10_scheduler_init() {
    _scheduler.init();

    // Register periodic tasks
    _scheduler.registerTask(INTERVAL_SENSOR_MS, onSampleTask, this);
    _scheduler.registerTask(INTERVAL_CHECKPOINT_MS, onCheckpointTask, this);
    _scheduler.registerTask(INTERVAL_HEARTBEAT_MS, onHeartbeatTask, this);
    _scheduler.registerTask(INTERVAL_HEALTH_MS, onHealthTask, this);
    _scheduler.registerTask(INTERVAL_DEVICE_POLL_MS, onDeviceRegistryPollTask, this);

    Serial.println("[BOOT] Stage 10: Scheduler Initialized [OK]");
    return true;
}

bool RuntimeManager::stage11_telemetry_init() {
    _telemetry.init();
    Serial.println("[BOOT] Stage 11: Telemetry Manager Initialized [OK]");
    return true;
}

bool RuntimeManager::stage12_security_init() {
    _security.init();
    Serial.println("[BOOT] Stage 12: Security Manager Initialized [OK]");
    return true;
}

bool RuntimeManager::stage13_runtime_ready() {
    // Inform backend that boot recovery was successful or defaults loaded
    bool recovered = (_state.checkpoint_id > 0);
    _protocol.sendMemoryStatus(
        recovered ? "restored" : "defaults_loaded",
        _state.model_v,
        recovered
    );
    _actuators.playBeep(2);
    Serial.println("[BOOT] Stage 13: System Runtime Ready [OK]");
    return true;
}

// ── Scheduler Task Callbacks ──────────────────────────────────────────────────
void RuntimeManager::onSampleTask(void* context) {
    RuntimeManager* mgr = static_cast<RuntimeManager*>(context);
    if (!mgr) return;

    // Increment frame sequence count
    mgr->_state.seq++;

    // Transmit telemetry
    mgr->_telemetry.transmit(&mgr->_state);

    // Evaluate fallback policy locally
    mgr->_local_policy.evaluate(mgr->_telemetry.getLatestReading(), &mgr->_state);
}

void RuntimeManager::onCheckpointTask(void* context) {
    RuntimeManager* mgr = static_cast<RuntimeManager*>(context);
    if (!mgr) return;

    mgr->_state.timestamp = millis();
    mgr->_checkpoint.save(&mgr->_state);
}

void RuntimeManager::onHeartbeatTask(void* context) {
    RuntimeManager* mgr = static_cast<RuntimeManager*>(context);
    if (!mgr) return;

    mgr->_protocol.sendHeartbeat(mgr->_state.seq, mgr->_state.model_v);
}

void RuntimeManager::onHealthTask(void* context) {
    RuntimeManager* mgr = static_cast<RuntimeManager*>(context);
    if (!mgr) return;

    mgr->_health.check();
}

void RuntimeManager::onDeviceRegistryPollTask(void* context) {
    RuntimeManager* mgr = static_cast<RuntimeManager*>(context);
    if (!mgr) return;

    // Timeout leaf devices after 1 minute of silence
    mgr->_device_registry.pollLiveness(60000);
}

// ── Inbound Command Handlers ──────────────────────────────────────────────────
void RuntimeManager::handlePolicyUpdate(const char* json_str) {
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, json_str);
    if (error) return;

    if (doc.containsKey("theta")) {
        _state.theta = doc["theta"];
    }

    const char* cmd_id = doc["command_id"] | "unknown";
    StaticJsonDocument<128> ack;
    ack["typ"] = "policy_ack";
    ack["command_id"] = cmd_id;

    char buf[128];
    serializeJson(ack, buf);
    _protocol.sendRaw(buf);

    _actuators.playBeep(1);
    _checkpoint.save(&_state);
}

void RuntimeManager::handleModelUpdate(const char* json_str) {
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, json_str);
    if (error) return;

    uint32_t model_v = doc["model_v"] | _state.model_v;
    float mean = doc["mean"] | _state.mean;
    float std_dev = doc["std"] | _state.std_dev;
    float theta = doc["theta"] | _state.theta;

    _model_runtime.updateModel(model_v, mean, std_dev, theta, &_state);

    const char* cmd_id = doc["command_id"] | "unknown";
    StaticJsonDocument<128> ack;
    ack["typ"] = "model_ack";
    ack["command_id"] = cmd_id;
    ack["model_v"] = _state.model_v;
    ack["status"] = "applied";

    char buf[128];
    serializeJson(ack, buf);
    _protocol.sendRaw(buf);

    _actuators.playBeep(2);
    _checkpoint.save(&_state);
}

void RuntimeManager::handleRelaySet(const char* json_str) {
    StaticJsonDocument<128> doc;
    DeserializationError error = deserializeJson(doc, json_str);
    if (error) return;

    bool relay_state = doc["state"];
    _actuators.setLed(relay_state);
}

void RuntimeManager::handleBuzzer(const char* json_str) {
    (void)json_str;
    _actuators.playBeep(1);
}

void RuntimeManager::handleCheckpoint(const char* json_str) {
    (void)json_str;
    _state.timestamp = millis();
    _checkpoint.save(&_state);
}
