/**
 * transport.h — Abstract communication interface.
 */
#pragma once
#include <stdint.h>

class ITransport {
public:
    virtual ~ITransport() {}

    virtual bool connect() = 0;
    virtual void disconnect() = 0;
    virtual bool send(const char* payload) = 0;
    virtual int  receive(char* buf, uint16_t max_len) = 0;
    virtual bool isConnected() = 0;
    virtual void flush() = 0;
    virtual bool reconnect() = 0;
    virtual void heartbeat() = 0;
};
