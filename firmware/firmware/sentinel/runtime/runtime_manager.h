/**
 * runtime_manager.h — Central system coordinator.
 */
#pragma once
#include "runtime_config.h"
#include "../storage/storage_manager.h"
#include "../storage/runtime_state.h"
#include "../checkpoint/checkpoint_manager.h"
#include "../sensors/sensor_driver.h"
#include "../features/feature_extractor.h"
#include "../actuators/actuator_driver.h"
#include "../communication/serial_transport.h"
#include "../communication/wifi_transport.h"
#include "../protocols/aeon_protocol.h"
#include "../protocols/command_router.h"
#include "../scheduler/scheduler.h"
#include "../telemetry/telemetry_manager.h"
#include "../inference/model_runtime.h"
#include "../inference/local_policy.h"
#include "../inference/rollback_manager.h"
#include "../devices/device_registry.h"
#include "../security/security_manager.h"
#include "../health/health_monitor.h"
#include "../inference/learning_engine.h"
#include "../inference/dream_state.h"

class RuntimeManager {
public:
    RuntimeManager();

    /** Starts the deterministic 13-stage boot pipeline. */
    bool boot();

    /** Main loop worker. Keeps transport ticking, scheduler running. */
    void tick();

    // ── Command Handlers (accessed by router callbacks) ──────────────────────
    void handlePolicyUpdate(const char* json_str);
    void handleModelUpdate(const char* json_str);
    void handleRelaySet(const char* json_str);
    void handleFanSet(const char* json_str);
    void handleBuzzer(const char* json_str);
    void handleCheckpoint(const char* json_str);

    // ── Deployment Lifecycle Handlers (Commit 3) ─────────────────────────────
    void handleDeploymentStart(const char* json_str);
    void handleDeploymentCommit(const char* json_str);
    void handleDeploymentRollback(const char* json_str);
    void handleStatisticsRequest(const char* json_str);

    // ── Adaptive Intelligence Handlers (Commit 4) ────────────────────────────
    void handleProfileUpdate(const char* json_str);
    void handleDecisionUpdate(const char* json_str);
    void handleContextSummary(const char* json_str);
    void handleActivitySummary(const char* json_str);

    // ── Cognitive OS Handlers (Commit 5) ─────────────────────────────────────
    void handleDecisionGenerated(const char* json_str);
    void handleExplanationGenerated(const char* json_str);
    void handleMemoryUpdated(const char* json_str);
    void handleReasoningCompleted(const char* json_str);
    void handleDeviceHealthUpdated(const char* json_str);
    void handleKnowledgeUpdated(const char* json_str);
    void handleConfidenceBreakdown(const char* json_str);

private:
    // Subsystem instances
    StorageManager    _storage;
    AeonState         _state;
    CheckpointManager _checkpoint;
    SensorDriver      _sensors;
    FeatureExtractor  _features;
    ActuatorDriver    _actuators;
    AeonSerialTransport   _transport;
    AeonProtocol      _protocol;
    CommandRouter     _router;
    Scheduler         _scheduler;
    TelemetryManager  _telemetry;
    ModelRuntime      _model_runtime;
    LocalPolicy       _local_policy;
    RollbackManager   _rollback_manager;
    DeviceRegistry    _device_registry;
    SecurityManager   _security;
    HealthMonitor     _health;
    LearningEngine    _learning_engine;
    DreamState        _dream_state;

    // Transient Adaptive State for Telemetry
    char     _current_activity[32];
    char     _selected_policy[32];
    float    _decision_confidence;

    // Timestamps for interval tracking (millis-based)
    uint32_t _last_stats_flush_ms;
    uint32_t _last_buffer_flush_ms;
    uint32_t _model_activated_at_ms;
    uint32_t _last_activity_ms;

    // Scheduled task callbacks (delegated to static helpers)
    static void onSampleTask(void* context);
    static void onCheckpointTask(void* context);
    static void onHeartbeatTask(void* context);
    static void onHealthTask(void* context);
    static void onDeviceRegistryPollTask(void* context);
    static void onStatisticsFlushTask(void* context);
    static void onLearningBufferFlushTask(void* context);
    static void onDreamTask(void* context);

    // Boot pipeline stages
    bool stage01_hardware_init();
    bool stage02_storage_init();
    bool stage03_config_load();
    bool stage04_checkpoint_recover();
    bool stage05_wifi_init();
    bool stage06_transport_init();
    bool stage07_device_registry_init();
    bool stage08_model_load();
    bool stage09_policy_init();
    bool stage10_scheduler_init();
    bool stage11_telemetry_init();
    bool stage12_security_init();
    bool stage13_runtime_ready();

    // Internal helpers
    void _flushStatistics();
    void _flushLearningBuffer();
};
