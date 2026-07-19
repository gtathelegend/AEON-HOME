/**
 * wifi_transport.cpp — WiFi and WebSocket transport implementation.
 */
#include "wifi_transport.h"
#include "../config.h"
#include <Arduino.h>

static WiFiTransport* g_wifi_transport_instance = nullptr;
static char s_rx_buffer[MAX_CMD_PAYLOAD];
static uint16_t s_rx_len = 0;
static bool s_rx_pending = false;

static void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    if (!g_wifi_transport_instance) return;
    switch(type) {
        case WStype_DISCONNECTED:
            // Handled internally or via check
            break;
        case WStype_CONNECTED:
            break;
        case WStype_TEXT:
            g_wifi_transport_instance->onMessageReceived((const char*)payload);
            break;
        default:
            break;
    }
}

WiFiTransport::WiFiTransport()
    : _connected(false), _last_reconnect_attempt(0) {
    g_wifi_transport_instance = this;
}

bool WiFiTransport::connect() {
#if defined(ARDUINO_UNO_Q)
    // 1. Initialize the Router Bridge to the Qualcomm MPU
    if (!Bridge.begin()) {
        return false;
    }
#else
    // 1. Connect to WiFi
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    unsigned long start_t = millis();
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        if (millis() - start_t > WIFI_CONNECT_TIMEOUT) {
            return false;
        }
    }
#endif

    // 2. Connect WebSocket
    _webSocket.begin(BACKEND_HOST, BACKEND_PORT, BACKEND_WS_PATH);
    _webSocket.onEvent(webSocketEvent);
    _webSocket.setReconnectInterval(WS_RECONNECT_INTERVAL);

    _connected = true;
    return true;
}

void WiFiTransport::disconnect() {
    _webSocket.disconnect();
#if !defined(ARDUINO_UNO_Q)
    WiFi.disconnect();
#endif
    _connected = false;
}

bool WiFiTransport::send(const char* payload) {
    if (!isConnected()) return false;
    return _webSocket.sendTXT(payload);
}

int WiFiTransport::receive(char* buf, uint16_t max_len) {
    if (!s_rx_pending) return 0;

    uint16_t copy_len = (s_rx_len < max_len) ? s_rx_len : (max_len - 1);
    memcpy(buf, s_rx_buffer, copy_len);
    buf[copy_len] = '\0';
    s_rx_pending = false;
    return copy_len;
}

bool WiFiTransport::isConnected() {
#if defined(ARDUINO_UNO_Q)
    return _webSocket.isConnected();
#else
    return (WiFi.status() == WL_CONNECTED) && _webSocket.isConnected();
#endif
}

void WiFiTransport::flush() {
    // WebSocketsClient does not require manual flushing
}

bool WiFiTransport::reconnect() {
    unsigned long now = millis();
    if (now - _last_reconnect_attempt >= WS_RECONNECT_INTERVAL) {
        _last_reconnect_attempt = now;
#if defined(ARDUINO_UNO_Q)
        // Bridge does not need manual reconnection as it is a local bus,
        // WebSocketsClient will auto-reconnect on the next tick.
#else
        if (WiFi.status() != WL_CONNECTED) {
            WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
        }
#endif
        return isConnected();
    }
    return false;
}

void WiFiTransport::heartbeat() {
    // WebSocket protocol layer takes care of ping/pong frames
}

void WiFiTransport::tick() {
    _webSocket.loop();
}

void WiFiTransport::onMessageReceived(const char* payload) {
    if (!payload) return;
    uint16_t len = strlen(payload);
    if (len >= MAX_CMD_PAYLOAD) {
        len = MAX_CMD_PAYLOAD - 1;
    }
    memcpy(s_rx_buffer, payload, len);
    s_rx_buffer[len] = '\0';
    s_rx_len = len;
    s_rx_pending = true;
}
