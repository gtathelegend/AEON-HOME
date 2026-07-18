#include "aeon_protocol.h"
#include <Arduino.h>
#include <SoftwareSerial.h>
#include <ArduinoJson.h>

static SoftwareSerial espSerial(10, 11); // RX, TX

void protocol_init(uint32_t debug_baud_rate, uint32_t esp_baud_rate) {
    Serial.begin(debug_baud_rate);
    espSerial.begin(esp_baud_rate);
}

void protocol_send_raw(const char* json) {
    // Mirror to debug, send to ESP
    Serial.println(json);
    espSerial.println(json);
}

void protocol_send_heartbeat(uint32_t seq, uint32_t model_v) {
    StaticJsonDocument<256> doc;
    doc["protocol_version"] = 1;
    doc["typ"] = "heartbeat";
    doc["device_id"] = "sentinel-01";
    doc["sequence"] = seq;
    doc["uptime_ms"] = millis();
    doc["model_v"] = model_v;

    char buffer[256];
    serializeJson(doc, buffer);
    protocol_send_raw(buffer);
}

void protocol_send_sensor_update(const SensorReading* reading, uint32_t seq, uint32_t model_v) {
    StaticJsonDocument<256> doc;
    doc["protocol_version"] = 1;
    doc["typ"] = "sensor_update";
    doc["device_id"] = "sentinel-01";
    doc["sequence"] = seq;
    doc["temp"] = reading->temperature;
    doc["humidity"] = reading->humidity;
    doc["motion"] = reading->motion ? 1 : 0;
    doc["model_v"] = model_v;

    char buffer[256];
    serializeJson(doc, buffer);
    protocol_send_raw(buffer);
}

#define AEON_MAX_PAYLOAD 256
static char rx_buffer[AEON_MAX_PAYLOAD + 1];
static uint16_t rx_index = 0;

void protocol_receive_byte(uint8_t b) {
    if (b == '\n' || b == '\r') {
        if (rx_index > 0) {
            rx_buffer[rx_index] = '\0';
            aeon_on_command(rx_buffer);
            rx_index = 0;
        }
    } else {
        if (rx_index < AEON_MAX_PAYLOAD) {
            rx_buffer[rx_index++] = b;
        } else {
            // Buffer overflow, drop it
            rx_index = 0;
        }
    }
}

void protocol_update() {
    while (espSerial.available() > 0) {
        uint8_t b = espSerial.read();
        protocol_receive_byte(b);
    }
}

