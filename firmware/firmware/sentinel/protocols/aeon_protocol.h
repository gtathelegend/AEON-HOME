/**
 * aeon_protocol.h — JSON message serialization/deserialization.
 */
#pragma once
#include <Arduino.h>
#include "../sensors/sensor_driver.h"
#include "../communication/transport.h"

class AeonProtocol {
public:
    AeonProtocol(ITransport& transport);

    void sendSensorUpdate(const SensorReading* reading, uint32_t seq, uint32_t model_v);
    void sendHeartbeat(uint32_t seq, uint32_t model_v);
    void sendMemoryStatus(const char* status, uint32_t model_v, bool checksum_valid);
    void sendFeedbackEvent(const char* event_name);
    void sendRaw(const char* json_str);

private:
    ITransport& _transport;
};
