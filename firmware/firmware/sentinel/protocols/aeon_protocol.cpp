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
