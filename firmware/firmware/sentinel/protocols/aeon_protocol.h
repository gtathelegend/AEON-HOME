#pragma once
#include <Arduino.h>
#include "../sensors/sensor_driver.h"
#include "../communication/transport.h"
#include "../inference/statistics_collector.h"

class AeonProtocol {
public:
    AeonProtocol(IAeonTransport& transport);

    // ── Existing messages ──────────────────────────────────────────────────
    void sendSensorUpdate(const SensorReading* reading, uint32_t seq, uint32_t model_v,
                          uint32_t profile_v = 0, float pref_temp = 21.0f,
                          const char* activity = "Idle", const char* policy = "background_policy",
                          float confidence = 1.0f);
    void sendHeartbeat(uint32_t seq, uint32_t model_v);
    void sendMemoryStatus(const char* status, uint32_t model_v, bool checksum_valid);
    void sendFeedbackEvent(const char* event_name);
    void sendRaw(const char* json_str);

    // ── Deployment lifecycle messages (added Commit 3) ─────────────────────

    /** Acknowledge a deployment_started command from the backend. */
    void sendDeploymentAck(const char* deployment_id, const char* status);

    /** Notify backend that a new model has been activated. */
    void sendModelActivated(uint32_t model_v, const char* deployment_id);

    /** Notify backend of a self-initiated firmware rollback. */
    void sendModelRolledBack(uint32_t model_v, const char* reason);

    /** Periodic statistics flush to backend. */
    void sendStatisticsUpdate(const RuntimeStats& stats, uint32_t model_v);

    /** Runtime health report (RAM, transport status). */
    void sendRuntimeHealth(bool ok, uint32_t free_ram_bytes, uint32_t model_v);

    /** Per-inference summary (fired every N inferences or on request). */
    void sendInferenceSummary(
        float confidence,
        uint32_t latency_ms,
        uint8_t prediction,
        bool success,
        uint32_t model_v
    );

    /** Report updated composite model score. */
    void sendModelScoreUpdated(float score, uint32_t model_v);

    /** Report learning buffer fill level. */
    void sendLearningBufferStatus(uint16_t count, uint16_t capacity);

    // ── Cognitive/Dream State messages (added Commit 6) ─────────────────────
    void sendDreamStarted();
    void sendDreamCompleted(uint32_t duration_ms, uint16_t consolidated_memories);
    void sendDreamInterrupted(const char* interrupt_reason);
    void sendLearningSummary(float overall_score, uint16_t feedback_count);
    void sendFeedbackReceived(const char* feedback_type, const char* target, float value);
    void sendRecommendationGenerated(const char* rec_id, const char* description);
    void sendKnowledgeUpdated(uint16_t node_count);
    void sendPreferenceUpdated(const char* pref_name, float value);
    void sendPolicyAdapted(const char* policy_name, float new_weight);
    void sendExperienceStored(const char* exp_id, bool success);
    void sendRuntimeEvaluation(float decision_quality, float override_freq);

private:
    IAeonTransport& _transport;
};
