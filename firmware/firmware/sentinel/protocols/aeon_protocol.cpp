/**
 * aeon_protocol.cpp — JSON serialization implementation.
 */
#include "aeon_protocol.h"
#include "../runtime/runtime_config.h"
#include <ArduinoJson.h>

AeonProtocol::AeonProtocol(IAeonTransport &transport) : _transport(transport) {}

void AeonProtocol::sendSensorUpdate(const SensorReading *reading, uint32_t seq,
                                    uint32_t model_v, uint32_t profile_v,
                                    float pref_temp, const char *activity,
                                    const char *policy, float confidence) {
  StaticJsonDocument<384> doc;
  doc["protocol_version"] = PROTOCOL_VERSION;
  doc["typ"] = "sensor_update";
  doc["device_id"] = DEVICE_ID;
  doc["sequence"] = seq;
  doc["temp"] = reading->temperature;
  doc["humidity"] = reading->humidity;
  doc["motion"] = reading->motion ? 1 : 0;
  doc["model_v"] = model_v;
  doc["profile_v"] = profile_v;
  doc["pref_temp"] = pref_temp;
  doc["activity"] = activity;
  doc["policy"] = policy;
  doc["confidence"] = confidence;

  char buffer[384];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendHeartbeat(uint32_t seq, uint32_t model_v) {
  StaticJsonDocument<256> doc;
  doc["protocol_version"] = PROTOCOL_VERSION;
  doc["typ"] = "heartbeat";
  doc["device_id"] = DEVICE_ID;
  doc["sequence"] = seq;
  doc["uptime_ms"] = millis();
  doc["model_v"] = model_v;

  char buffer[256];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendMemoryStatus(const char *status, uint32_t model_v,
                                    bool checksum_valid) {
  StaticJsonDocument<256> doc;
  doc["typ"] = "memory_status";
  doc["device_id"] = DEVICE_ID;
  doc["status"] = status;
  doc["model_v"] = model_v;
  doc["checksum_valid"] = checksum_valid;

  char buffer[256];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendFeedbackEvent(const char *event_name) {
  StaticJsonDocument<256> doc;
  doc["typ"] = "feedback_event";
  doc["device_id"] = DEVICE_ID;
  doc["event"] = event_name;

  char buffer[256];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendRaw(const char *json_str) {
  _transport.send(json_str);
}

// ── Deployment lifecycle messages
// ─────────────────────────────────────────────

void AeonProtocol::sendDeploymentAck(const char *deployment_id,
                                     const char *status) {
  StaticJsonDocument<256> doc;
  doc["typ"] = "deployment_ack";
  doc["device_id"] = DEVICE_ID;
  doc["deployment_id"] = deployment_id;
  doc["status"] = status;
  doc["ts_ms"] = millis();

  char buffer[256];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendModelActivated(uint32_t model_v,
                                      const char *deployment_id) {
  StaticJsonDocument<256> doc;
  doc["typ"] = "model_activated";
  doc["device_id"] = DEVICE_ID;
  doc["model_v"] = model_v;
  doc["deployment_id"] = deployment_id;
  doc["ts_ms"] = millis();

  char buffer[256];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendModelRolledBack(uint32_t model_v, const char *reason) {
  StaticJsonDocument<256> doc;
  doc["typ"] = "model_rolled_back";
  doc["device_id"] = DEVICE_ID;
  doc["model_v"] = model_v;
  doc["reason"] = reason;
  doc["ts_ms"] = millis();

  char buffer[256];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendStatisticsUpdate(const RuntimeStats &stats,
                                        uint32_t model_v) {
  StaticJsonDocument<384> doc;
  doc["typ"] = "statistics_updated";
  doc["device_id"] = DEVICE_ID;
  doc["model_v"] = model_v;
  doc["inference_count"] = stats.total_inferences;
  doc["avg_confidence"] = stats.avg_confidence;
  doc["avg_latency_ms"] = stats.avg_latency_ms;
  doc["error_count"] = stats.error_count;
  doc["error_rate"] = stats.error_rate;
  doc["rollback_count"] = stats.rollback_count;
  doc["ts_ms"] = millis();

  char buffer[384];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendRuntimeHealth(bool ok, uint32_t free_ram_bytes,
                                     uint32_t model_v) {
  StaticJsonDocument<256> doc;
  doc["typ"] = "runtime_health";
  doc["device_id"] = DEVICE_ID;
  doc["ok"] = ok;
  doc["free_ram_bytes"] = free_ram_bytes;
  doc["model_v"] = model_v;
  doc["uptime_ms"] = millis();

  char buffer[256];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendInferenceSummary(float confidence, uint32_t latency_ms,
                                        uint8_t prediction, bool success,
                                        uint32_t model_v) {
  StaticJsonDocument<256> doc;
  doc["typ"] = "inference_summary";
  doc["device_id"] = DEVICE_ID;
  doc["model_v"] = model_v;
  doc["confidence"] = confidence;
  doc["latency_ms"] = latency_ms;
  doc["prediction"] = prediction;
  doc["success"] = success;
  doc["ts_ms"] = millis();

  char buffer[256];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendModelScoreUpdated(float score, uint32_t model_v) {
  StaticJsonDocument<128> doc;
  doc["typ"] = "model_score_updated";
  doc["device_id"] = DEVICE_ID;
  doc["model_v"] = model_v;
  doc["score"] = score;
  doc["ts_ms"] = millis();

  char buffer[128];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendLearningBufferStatus(uint16_t count, uint16_t capacity) {
  StaticJsonDocument<128> doc;
  doc["typ"] = "learning_buffer_status";
  doc["device_id"] = DEVICE_ID;
  doc["count"] = count;
  doc["capacity"] = capacity;
  doc["ts_ms"] = millis();

  char buffer[128];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendDreamStarted() {
  StaticJsonDocument<128> doc;
  doc["typ"] = "dream_started";
  doc["device_id"] = DEVICE_ID;
  doc["ts_ms"] = millis();

  char buffer[128];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendDreamCompleted(uint32_t duration_ms,
                                      uint16_t consolidated_memories) {
  StaticJsonDocument<192> doc;
  doc["typ"] = "dream_completed";
  doc["device_id"] = DEVICE_ID;
  doc["duration_ms"] = duration_ms;
  doc["consolidated_memories"] = consolidated_memories;
  doc["ts_ms"] = millis();

  char buffer[192];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendDreamInterrupted(const char *interrupt_reason) {
  StaticJsonDocument<192> doc;
  doc["typ"] = "dream_interrupted";
  doc["device_id"] = DEVICE_ID;
  doc["reason"] = interrupt_reason;
  doc["ts_ms"] = millis();

  char buffer[192];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendLearningSummary(float overall_score,
                                       uint16_t feedback_count) {
  StaticJsonDocument<192> doc;
  doc["typ"] = "learning_summary";
  doc["device_id"] = DEVICE_ID;
  doc["overall_score"] = overall_score;
  doc["feedback_count"] = feedback_count;
  doc["ts_ms"] = millis();

  char buffer[192];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendFeedbackReceived(const char *feedback_type,
                                        const char *target, float value) {
  StaticJsonDocument<256> doc;
  doc["typ"] = "feedback_received";
  doc["device_id"] = DEVICE_ID;
  doc["feedback_type"] = feedback_type;
  doc["target"] = target;
  doc["value"] = value;
  doc["ts_ms"] = millis();

  char buffer[256];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendRecommendationGenerated(const char *rec_id,
                                               const char *description) {
  StaticJsonDocument<256> doc;
  doc["typ"] = "recommendation_generated";
  doc["device_id"] = DEVICE_ID;
  doc["rec_id"] = rec_id;
  doc["description"] = description;
  doc["ts_ms"] = millis();

  char buffer[256];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendKnowledgeUpdated(uint16_t node_count) {
  StaticJsonDocument<128> doc;
  doc["typ"] = "knowledge_updated";
  doc["device_id"] = DEVICE_ID;
  doc["node_count"] = node_count;
  doc["ts_ms"] = millis();

  char buffer[128];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendPreferenceUpdated(const char *pref_name, float value) {
  StaticJsonDocument<192> doc;
  doc["typ"] = "preference_updated";
  doc["device_id"] = DEVICE_ID;
  doc["pref_name"] = pref_name;
  doc["value"] = value;
  doc["ts_ms"] = millis();

  char buffer[192];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendPolicyAdapted(const char *policy_name,
                                     float new_weight) {
  StaticJsonDocument<192> doc;
  doc["typ"] = "policy_adapted";
  doc["device_id"] = DEVICE_ID;
  doc["policy_name"] = policy_name;
  doc["new_weight"] = new_weight;
  doc["ts_ms"] = millis();

  char buffer[192];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendExperienceStored(const char *exp_id, bool success) {
  StaticJsonDocument<192> doc;
  doc["typ"] = "experience_stored";
  doc["device_id"] = DEVICE_ID;
  doc["exp_id"] = exp_id;
  doc["success"] = success;
  doc["ts_ms"] = millis();

  char buffer[192];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}

void AeonProtocol::sendRuntimeEvaluation(float decision_quality,
                                         float override_freq) {
  StaticJsonDocument<192> doc;
  doc["typ"] = "runtime_evaluation";
  doc["device_id"] = DEVICE_ID;
  doc["decision_quality"] = decision_quality;
  doc["override_freq"] = override_freq;
  doc["ts_ms"] = millis();

  char buffer[192];
  serializeJson(doc, buffer);
  sendRaw(buffer);
}
