/**
 * aeon_protocol.cpp — JSON serialization implementation.
 */
#include "aeon_protocol.h"
#include "../runtime/runtime_config.h"
#include <ArduinoJson.h>

AeonProtocol::AeonProtocol(ITransport& transport)
    : _transport(transport) {}

void AeonProtocol::sendSensorUpdate(const SensorReading* reading, uint32_t seq, uint32_t model_v) {
    StaticJsonDocument<256> doc;
    doc["protocol_version"] = PROTOCOL_VERSION;
    doc["typ"] = "sensor_update";
    doc["device_id"] = DEVICE_ID;
    doc["sequence"] = seq;
    doc["temp"] = reading->temperature;
    doc["humidity"] = reading->humidity;
    doc["motion"] = reading->motion ? 1 : 0;
    doc["model_v"] = model_v;

    char buffer[256];
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

void AeonProtocol::sendMemoryStatus(const char* status, uint32_t model_v, bool checksum_valid) {
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

void AeonProtocol::sendFeedbackEvent(const char* event_name) {
    StaticJsonDocument<256> doc;
    doc["typ"] = "feedback_event";
    doc["device_id"] = DEVICE_ID;
    doc["event"] = event_name;

    char buffer[256];
    serializeJson(doc, buffer);
    sendRaw(buffer);
}

void AeonProtocol::sendRaw(const char* json_str) {
    // Print to debug serial for local logging, and send via transport
    Serial.println(json_str);
    _transport.send(json_str);
}

// ── Deployment lifecycle messages ─────────────────────────────────────────────

void AeonProtocol::sendDeploymentAck(const char* deployment_id, const char* status) {
    StaticJsonDocument<256> doc;
    doc["typ"]           = "deployment_ack";
    doc["device_id"]     = DEVICE_ID;
    doc["deployment_id"] = deployment_id;
    doc["status"]        = status;
    doc["ts_ms"]         = millis();

    char buffer[256];
    serializeJson(doc, buffer);
    sendRaw(buffer);
}

void AeonProtocol::sendModelActivated(uint32_t model_v, const char* deployment_id) {
    StaticJsonDocument<256> doc;
    doc["typ"]           = "model_activated";
    doc["device_id"]     = DEVICE_ID;
    doc["model_v"]       = model_v;
    doc["deployment_id"] = deployment_id;
    doc["ts_ms"]         = millis();

    char buffer[256];
    serializeJson(doc, buffer);
    sendRaw(buffer);
}

void AeonProtocol::sendModelRolledBack(uint32_t model_v, const char* reason) {
    StaticJsonDocument<256> doc;
    doc["typ"]       = "model_rolled_back";
    doc["device_id"] = DEVICE_ID;
    doc["model_v"]   = model_v;
    doc["reason"]    = reason;
    doc["ts_ms"]     = millis();

    char buffer[256];
    serializeJson(doc, buffer);
    sendRaw(buffer);
}

void AeonProtocol::sendStatisticsUpdate(const RuntimeStats& stats, uint32_t model_v) {
    StaticJsonDocument<384> doc;
    doc["typ"]               = "statistics_updated";
    doc["device_id"]         = DEVICE_ID;
    doc["model_v"]           = model_v;
    doc["inference_count"]   = stats.total_inferences;
    doc["avg_confidence"]    = stats.avg_confidence;
    doc["avg_latency_ms"]    = stats.avg_latency_ms;
    doc["error_count"]       = stats.error_count;
    doc["error_rate"]        = stats.error_rate;
    doc["rollback_count"]    = stats.rollback_count;
    doc["ts_ms"]             = millis();

    char buffer[384];
    serializeJson(doc, buffer);
    sendRaw(buffer);
}

void AeonProtocol::sendRuntimeHealth(bool ok, uint32_t free_ram_bytes, uint32_t model_v) {
    StaticJsonDocument<256> doc;
    doc["typ"]            = "runtime_health";
    doc["device_id"]      = DEVICE_ID;
    doc["ok"]             = ok;
    doc["free_ram_bytes"] = free_ram_bytes;
    doc["model_v"]        = model_v;
    doc["uptime_ms"]      = millis();

    char buffer[256];
    serializeJson(doc, buffer);
    sendRaw(buffer);
}

void AeonProtocol::sendInferenceSummary(
    float confidence, uint32_t latency_ms,
    uint8_t prediction, bool success, uint32_t model_v)
{
    StaticJsonDocument<256> doc;
    doc["typ"]        = "inference_summary";
    doc["device_id"]  = DEVICE_ID;
    doc["model_v"]    = model_v;
    doc["confidence"] = confidence;
    doc["latency_ms"] = latency_ms;
    doc["prediction"] = prediction;
    doc["success"]    = success;
    doc["ts_ms"]      = millis();

    char buffer[256];
    serializeJson(doc, buffer);
    sendRaw(buffer);
}

void AeonProtocol::sendModelScoreUpdated(float score, uint32_t model_v) {
    StaticJsonDocument<128> doc;
    doc["typ"]       = "model_score_updated";
    doc["device_id"] = DEVICE_ID;
    doc["model_v"]   = model_v;
    doc["score"]     = score;
    doc["ts_ms"]     = millis();

    char buffer[128];
    serializeJson(doc, buffer);
    sendRaw(buffer);
}

void AeonProtocol::sendLearningBufferStatus(uint16_t count, uint16_t capacity) {
    StaticJsonDocument<128> doc;
    doc["typ"]       = "learning_buffer_status";
    doc["device_id"] = DEVICE_ID;
    doc["count"]     = count;
    doc["capacity"]  = capacity;
    doc["ts_ms"]     = millis();

    char buffer[128];
    serializeJson(doc, buffer);
    sendRaw(buffer);
}

