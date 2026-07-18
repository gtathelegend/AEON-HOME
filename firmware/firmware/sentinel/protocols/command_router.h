/**
 * command_router.h — Parses and routes inbound JSON commands.
 */
#pragma once
#include <Arduino.h>

class CommandRouter {
public:
    typedef void (*CommandHandler)(const char* typ, const char* json_str, void* context);

    CommandRouter();

    /** Register a handler for a specific command type. */
    void registerHandler(const char* typ, CommandHandler handler, void* context);

    /** Parse an incoming JSON string and route it to the correct handler. */
    void route(const char* json_str);

private:
    struct HandlerEntry {
        char typ[32];
        CommandHandler handler;
        void* context;
    };

    static const uint8_t MAX_HANDLERS = 8;
    HandlerEntry _handlers[MAX_HANDLERS];
    uint8_t _handler_count;
};
