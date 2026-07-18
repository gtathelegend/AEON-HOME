/**
 * runtime_manager.cpp — Main system coordinator implementation.
 */
#include "runtime_manager.h"
#include <ArduinoJson.h>

// ── Router Callback Wrapper ──────────────────────────────────────────────────
static void routerCallback(const char* typ, const char* json_str, void* context) {
    RuntimeManager* mgr = static_cast<RuntimeManager*>(context);
    if (!mgr) return;

    if      (strcmp(typ, "policy_update")       == 0) mgr->handlePolicyUpdate(json_str);
    else if (strcmp(typ, "model_update")        == 0) mgr->handleModelUpdate(json_str);
    else if (strcmp(typ, "relay_set")           == 0) mgr->handleRelaySet(json_str);
    else if (strcmp(typ, "buzzer")              == 0) mgr->handleBuzzer(json_str);
    else if (strcmp(typ, "checkpoint")          == 0) mgr->handleCheckpoint(json_str);
    else if (strcmp(typ, "deployment_start")    == 0) mgr->handleDeploymentStart(json_str);
    else if (strcmp(typ, "deployment_commit")   == 0) mgr->handleDeploymentCommit(json_str);
    else if (strcmp(typ, "deployment_rollback") == 0) mgr->handleDeploymentRollback(json_str);
    else if (strcmp(typ, "statistics_request")  == 0) mgr->handleStatisticsRequest(json_str);
}

// ── Constructor ──────────────────────────────────────────────────────────────
RuntimeManager::RuntimeManager()
    : _checkpoint(_storage),
      _protocol(_transport),
      _telemetry(_sensors, _features, _protocol),
      _local_policy(_actuators, _protocol),
      _rollback_manager(_model_runtime, _protocol, _checkpoint),
      _health(_transport),
      _last_stats_flush_ms(0),
      _last_buffer_flush_ms(0),
      _model_activated_at_ms(0)
{}

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
    bool ok = _transport.connect();
    if (ok) {
        Serial.println("[BOOT] Stage 5: WiFi association [OK]");
    } else {
        Serial.println("[BOOT] Stage 5: WiFi association [FAIL]");
    }
    return true;
}

bool RuntimeManager::stage06_transport_init() {
    Serial.println("[BOOT] Stage 6: Transport Initialization [OK]");
    return true;
}

bool RuntimeManager::stage07_device_registry_init() {
    _device_registry.init();
    Serial.println("[BOOT] Stage 7: Device Registry Initialized [OK]");
    return true;
}

bool RuntimeManager::stage08_model_load() {
    // Initialize ModelRuntime and restore stats from persisted AeonState.
    // The state was already restored in stage04 so we pass it directly.
    _model_runtime.init(&_state);
    _model_activated_at_ms = millis();
    Serial.print("[BOOT] Stage 8: Model Loading [OK] Model V: ");
    Serial.println(_state.model_v);
    return true;
}

bool RuntimeManager::stage09_policy_init() {
    _local_policy.init();

    // Register router command callbacks (original + new deployment commands)
    _router.registerHandler("policy_update",       routerCallback, this);
    _router.registerHandler("model_update",        routerCallback, this);
    _router.registerHandler("relay_set",           routerCallback, this);
    _router.registerHandler("buzzer",              routerCallback, this);
    _router.registerHandler("checkpoint",          routerCallback, this);
    _router.registerHandler("deployment_start",    routerCallback, this);
    _router.registerHandler("deployment_commit",   routerCallback, this);
    _router.registerHandler("deployment_rollback", routerCallback, this);
    _router.registerHandler("statistics_request",  routerCallback, this);

    Serial.println("[BOOT] Stage 9: Policy Engine Initialized [OK]");
    return true;
}

bool RuntimeManager::stage10_scheduler_init() {
    _scheduler.init();

    // Original tasks
    _scheduler.registerTask(INTERVAL_SENSOR_MS,       onSampleTask,              this);
    _scheduler.registerTask(INTERVAL_CHECKPOINT_MS,   onCheckpointTask,          this);
    _scheduler.registerTask(INTERVAL_HEARTBEAT_MS,    onHeartbeatTask,           this);
    _scheduler.registerTask(INTERVAL_HEALTH_MS,       onHealthTask,              this);
    _scheduler.registerTask(INTERVAL_DEVICE_POLL_MS,  onDeviceRegistryPollTask,  this);

    // New tasks (Commit 3)
    _scheduler.registerTask(STATISTICS_FLUSH_INTERVAL_MS,  onStatisticsFlushTask,      this);
    _scheduler.registerTask(LEARNING_BUFFER_FLUSH_MS,       onLearningBufferFlushTask,  this);

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

    mgr->_state.seq++;

    // Transmit sensor telemetry
    mgr->_telemetry.transmit(&mgr->_state);

    // Run on-device inference using ModelRuntime
    const SensorReading* reading = mgr->_telemetry.getLatestReading();
    if (reading) {
        InferenceResult result = mgr->_model_runtime.executeInference(
            reading->temperature,
            mgr->_state.seq,
            millis()
        );

        // Record in learning buffer (no override on regular inference)
        float feature_vec[FEATURE_VECTOR_LEN] = {
            reading->temperature,
            reading->humidity,
            reading->motion ? 1.0f : 0.0f,
            0.0f,  // door_open placeholder
            reading->temperature,  // mean_temp (simplified)
            0.0f,                  // var_temp placeholder
            0.0f,                  // delta_motion placeholder
        };
        mgr->_model_runtime.recordForLearning(
            result, feature_vec, mgr->_state.seq, millis(), false
        );

        // Send inference summary to backend every 10 inferences
        if ((mgr->_state.seq % 10) == 0) {
            mgr->_protocol.sendInferenceSummary(
                result.confidence.final_confidence,
                result.latency_ms,
                result.prediction,
                result.success,
                mgr->_state.model_v
            );
        }
    }

    // Evaluate fallback policy locally
    mgr->_local_policy.evaluate(mgr->_telemetry.getLatestReading(), &mgr->_state);
}

void RuntimeManager::onCheckpointTask(void* context) {
    RuntimeManager* mgr = static_cast<RuntimeManager*>(context);
    if (!mgr) return;

    mgr->_state.timestamp = millis();
    mgr->_model_runtime.persistStats(&mgr->_state);
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

    // Also send runtime health with approximate free RAM
    // (On STM32, we can estimate free RAM from stack/heap gap)
    uint32_t free_ram = 0;  // Platform-specific — placeholder
    mgr->_protocol.sendRuntimeHealth(true, free_ram, mgr->_state.model_v);

    // Check rollback conditions after health tick
    const RuntimeStats& stats = mgr->_model_runtime.statistics().getStats();
    ModelScoreResult score = mgr->_model_runtime.computeScore(
        (millis() - mgr->_model_activated_at_ms) / 1000u
    );
    RollbackTrigger trigger = mgr->_rollback_manager.evaluate(stats, score, &mgr->_state);
    if (trigger != ROLLBACK_NONE) {
        mgr->_actuators.playBeep(3);  // Alert on rollback
    }
}

void RuntimeManager::onDeviceRegistryPollTask(void* context) {
    RuntimeManager* mgr = static_cast<RuntimeManager*>(context);
    if (!mgr) return;

    mgr->_device_registry.pollLiveness(60000);
}

void RuntimeManager::onStatisticsFlushTask(void* context) {
    RuntimeManager* mgr = static_cast<RuntimeManager*>(context);
    if (!mgr) return;

    mgr->_flushStatistics();
}

void RuntimeManager::onLearningBufferFlushTask(void* context) {
    RuntimeManager* mgr = static_cast<RuntimeManager*>(context);
    if (!mgr) return;

    mgr->_flushLearningBuffer();
}

void RuntimeManager::_flushStatistics() {
    const RuntimeStats& stats = _model_runtime.statistics().getStats();
    _protocol.sendStatisticsUpdate(stats, _state.model_v);

    // Also report current composite score
    ModelScoreResult score = _model_runtime.computeScore(
        (millis() - _model_activated_at_ms) / 1000u
    );
    _protocol.sendModelScoreUpdated(score.composite_score, _state.model_v);

    // Persist stats to flash
    _model_runtime.persistStats(&_state);
    _checkpoint.save(&_state);
}

void RuntimeManager::_flushLearningBuffer() {
    LearningBuffer& buf = _model_runtime.learningBuffer();
    _protocol.sendLearningBufferStatus(buf.count(), buf.capacity());

    if (buf.count() > 0) {
        buf.flush(_transport, &_state);
    }
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
    ack["typ"]        = "policy_ack";
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
    float mean       = doc["mean"]    | _state.mean;
    float std_dev    = doc["std"]     | _state.std_dev;
    float theta      = doc["theta"]   | _state.theta;

    // Delegate to new ModelRuntime (backward-compatible path)
    _model_runtime.updateModel(model_v, mean, std_dev, theta, &_state);
    _rollback_manager.reset();

    const char* cmd_id = doc["command_id"] | "unknown";
    StaticJsonDocument<128> ack;
    ack["typ"]        = "model_ack";
    ack["command_id"] = cmd_id;
    ack["model_v"]    = _state.model_v;
    ack["status"]     = "applied";

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
    _model_runtime.persistStats(&_state);
    _checkpoint.save(&_state);
}

// ── Deployment Lifecycle Handlers (Commit 3) ─────────────────────────────────

void RuntimeManager::handleDeploymentStart(const char* json_str) {
    StaticJsonDocument<384> doc;
    DeserializationError error = deserializeJson(doc, json_str);
    if (error) {
        _protocol.sendDeploymentAck("unknown", "parse_error");
        return;
    }

    DeploymentManifest manifest;
    manifest.deployment_id    = doc["deployment_id"] | (uint32_t)0;
    manifest.model_version    = doc["model_v"]       | (uint32_t)_state.model_v;
    manifest.mean             = doc["mean"]           | _state.mean;
    manifest.std_dev          = doc["std_dev"]        | _state.std_dev;
    manifest.theta            = doc["theta"]          | _state.theta;
    manifest.accuracy_estimate = doc["accuracy"]      | 0.0f;

    const char* checksum = doc["checksum"] | "";
    strncpy(manifest.checksum, checksum, sizeof(manifest.checksum) - 1);
    manifest.checksum[sizeof(manifest.checksum) - 1] = '\0';

    _model_runtime.loadDeployment(manifest, &_state);

    // Acknowledge receipt
    char dep_id_str[20];
    snprintf(dep_id_str, sizeof(dep_id_str), "%lu", (unsigned long)manifest.deployment_id);
    _protocol.sendDeploymentAck(dep_id_str, "received");

    Serial.println("[Deploy] Deployment staged. Awaiting commit.");
}

void RuntimeManager::handleDeploymentCommit(const char* json_str) {
    StaticJsonDocument<128> doc;
    deserializeJson(doc, json_str);

    _model_runtime.activateCandidate(&_state);
    _rollback_manager.reset();
    _model_activated_at_ms = millis();

    // Flush stats reset to flash
    _model_runtime.persistStats(&_state);
    _checkpoint.save(&_state);

    char dep_id_str[20];
    snprintf(dep_id_str, sizeof(dep_id_str), "%lu", (unsigned long)_state.deployment_id);
    _protocol.sendModelActivated(_state.model_v, dep_id_str);

    _actuators.playBeep(3);  // Three beeps = model activated
    Serial.print("[Deploy] Model activated: v");
    Serial.println(_state.model_v);
}

void RuntimeManager::handleDeploymentRollback(const char* json_str) {
    (void)json_str;

    _model_runtime.rollbackToPrevious(&_state);
    _rollback_manager.reset();

    _model_runtime.persistStats(&_state);
    _checkpoint.save(&_state);

    // sendModelRolledBack is called inside RollbackManager / rollbackToPrevious
    _actuators.playBeep(4);  // Four beeps = rollback
    Serial.println("[Deploy] Manual rollback executed.");
}

void RuntimeManager::handleStatisticsRequest(const char* json_str) {
    (void)json_str;
    _flushStatistics();
}
