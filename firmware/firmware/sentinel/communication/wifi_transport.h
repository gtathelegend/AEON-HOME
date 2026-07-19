/**
 * wifi_transport.h — WiFi and WebSocket implementation of ITransport.
 */
#pragma once
#include "transport.h"
#include "../runtime/runtime_config.h"

#if defined(ARDUINO_UNOWIFIR4)
#include <WiFiS3.h>
#elif defined(ARDUINO_UNO_Q)
// Native support is implemented directly in the WebSockets library for ARDUINO_UNO_Q.
#else
#include <WiFi.h>
#endif

#include <WebSocketsClient.h>

class WiFiTransport : public IAeonTransport {
public:
    WiFiTransport();

    virtual bool connect() override;
    virtual void disconnect() override;
    virtual bool send(const char* payload) override;
    virtual int  receive(char* buf, uint16_t max_len) override;
    virtual bool isConnected() override;
    virtual void flush() override;
    virtual bool reconnect() override;
    virtual void heartbeat() override;

    // Tick method to keep WebSocket connection alive
    void tick();

    // Callback when text is received
    void onMessageReceived(const char* payload);

private:
    WebSocketsClient _webSocket;
    bool _connected;
    unsigned long _last_reconnect_attempt;
};
