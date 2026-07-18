/**
 * command_router.cpp — Command router implementation.
 */
#include "command_router.h"
#include <ArduinoJson.h>
#include <string.h>

CommandRouter::CommandRouter()
    : _handler_count(0) {}

void CommandRouter::registerHandler(const char* typ, CommandHandler handler, void* context) {
    if (_handler_count >= MAX_HANDLERS || !typ || !handler) return;

    strncpy(_handlers[_handler_count].typ, typ, 31);
    _handlers[_handler_count].typ[31] = '\0';
    _handlers[_handler_count].handler = handler;
    _handlers[_handler_count].context = context;
    _handler_count++;
}

void CommandRouter::route(const char* json_str) {
    if (!json_str) return;

    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, json_str);
    if (error) return;

    const char* typ = doc["typ"];
    if (!typ) return;

    for (uint8_t i = 0; i < _handler_count; i++) {
        if (strcmp(_handlers[i].typ, typ) == 0) {
            _handlers[i].handler(typ, json_str, _handlers[i].context);
            return;
        }
    }
}
