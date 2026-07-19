/**
 * serial_transport.h — USB Serial implementation of IAeonTransport for Arduino UNO Q.
 */
#pragma once
#include "transport.h"
#include "../runtime/runtime_config.h"
#include <Arduino.h>

class AeonSerialTransport : public IAeonTransport {
public:
    AeonSerialTransport(uint32_t baud = 115200);

    virtual bool connect() override;
    virtual void disconnect() override;
    virtual bool send(const char* payload) override;
    virtual int  receive(char* buf, uint16_t max_len) override;
    virtual bool isConnected() override;
    virtual void flush() override;
    virtual bool reconnect() override;
    virtual void heartbeat() override;

    // Periodic worker to poll USB Serial input buffer
    void tick();

    // Callback when a complete line is received
    void onLineReceived(const char* payload);

private:
    uint32_t _baud;
    bool _connected;
};
