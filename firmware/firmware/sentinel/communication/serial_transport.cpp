/**
 * serial_transport.cpp — USB Serial transport implementation.
 */
#include "serial_transport.h"
#include "../config.h"
#include <Arduino.h>

static char s_serial_rx_buffer[MAX_CMD_PAYLOAD];
static uint16_t s_serial_rx_len = 0;
static bool s_serial_rx_pending = false;

static char s_line_accum_buffer[MAX_CMD_PAYLOAD];
static uint16_t s_line_accum_pos = 0;

AeonSerialTransport::AeonSerialTransport(uint32_t baud)
    : _baud(baud), _connected(false) {}

bool AeonSerialTransport::connect() {
    if (!Serial) {
        Serial.begin(_baud);
        uint32_t start_ms = millis();
        while (!Serial && (millis() - start_ms < 2000)) {
            delay(10);
        }
    }
    _connected = true;
    return true;
}

void AeonSerialTransport::disconnect() {
    _connected = false;
}

bool AeonSerialTransport::send(const char* payload) {
    if (!payload || !_connected) return false;
    Serial.println(payload);
    Serial.flush();
    return true;
}

int AeonSerialTransport::receive(char* buf, uint16_t max_len) {
    if (!s_serial_rx_pending || !buf || max_len == 0) return 0;

    uint16_t copy_len = (s_serial_rx_len < max_len) ? s_serial_rx_len : (max_len - 1);
    memcpy(buf, s_serial_rx_buffer, copy_len);
    buf[copy_len] = '\0';
    s_serial_rx_pending = false;
    return copy_len;
}

bool AeonSerialTransport::isConnected() {
    return _connected && bool(Serial);
}

void AeonSerialTransport::flush() {
    if (Serial) {
        Serial.flush();
    }
}

bool AeonSerialTransport::reconnect() {
    return connect();
}

void AeonSerialTransport::heartbeat() {
    // Serial port does not require active keep-alive frames
}

void AeonSerialTransport::tick() {
    if (!Serial) return;

    while (Serial.available() > 0) {
        int ch = Serial.read();
        if (ch < 0) break;

        if (ch == '\n' || ch == '\r') {
            if (s_line_accum_pos > 0) {
                s_line_accum_buffer[s_line_accum_pos] = '\0';
                onLineReceived(s_line_accum_buffer);
                s_line_accum_pos = 0;
            }
        } else {
            if (s_line_accum_pos < (sizeof(s_line_accum_buffer) - 1)) {
                s_line_accum_buffer[s_line_accum_pos++] = (char)ch;
            } else {
                // Truncate overflow line safely
                s_line_accum_buffer[sizeof(s_line_accum_buffer) - 1] = '\0';
                onLineReceived(s_line_accum_buffer);
                s_line_accum_pos = 0;
            }
        }
    }
}

void AeonSerialTransport::onLineReceived(const char* payload) {
    if (!payload) return;
    uint16_t len = strlen(payload);
    if (len >= MAX_CMD_PAYLOAD) {
        len = MAX_CMD_PAYLOAD - 1;
    }
    memcpy(s_serial_rx_buffer, payload, len);
    s_serial_rx_buffer[len] = '\0';
    s_serial_rx_len = len;
    s_serial_rx_pending = true;
}
