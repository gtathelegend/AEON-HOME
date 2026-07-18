/**
 * device_registry.cpp — Device registry implementation.
 */
#include "device_registry.h"
#include <string.h>

DeviceRegistry::DeviceRegistry()
    : _count(0) {}

void DeviceRegistry::init() {
    _count = 0;
    // Register self at boot
    registerDevice("sentinel-01", "mcu_gateway", "2.0.0");
}

bool DeviceRegistry::registerDevice(const char* id, const char* type, const char* version) {
    if (!id || !type || !version) return false;

    // Check if already registered
    for (uint8_t i = 0; i < _count; i++) {
        if (strcmp(_devices[i].id, id) == 0) {
            strncpy(_devices[i].version, version, 7);
            _devices[i].version[7] = '\0';
            _devices[i].last_seen_ms = millis();
            _devices[i].online = true;
            return true;
        }
    }

    if (_count >= MAX_DEVICES) return false;

    strncpy(_devices[_count].id, id, 15);
    _devices[_count].id[15] = '\0';
    strncpy(_devices[_count].type, type, 15);
    _devices[_count].type[15] = '\0';
    strncpy(_devices[_count].version, version, 7);
    _devices[_count].version[7] = '\0';
    _devices[_count].online = true;
    _devices[_count].last_seen_ms = millis();
    _devices[_count].rssi = 0;
    _count++;
    return true;
}

void DeviceRegistry::updateLiveness(const char* id, int rssi) {
    if (!id) return;
    for (uint8_t i = 0; i < _count; i++) {
        if (strcmp(_devices[i].id, id) == 0) {
            _devices[i].last_seen_ms = millis();
            _devices[i].online = true;
            _devices[i].rssi = rssi;
            return;
        }
    }
}

void DeviceRegistry::pollLiveness(unsigned long timeout_ms) {
    unsigned long now = millis();
    for (uint8_t i = 0; i < _count; i++) {
        // sentinel-01 is self, always online
        if (strcmp(_devices[i].id, "sentinel-01") == 0) {
            _devices[i].online = true;
            _devices[i].last_seen_ms = now;
            continue;
        }

        if (now - _devices[i].last_seen_ms > timeout_ms) {
            _devices[i].online = false;
        }
    }
}

const DeviceRecord* DeviceRegistry::getDeviceByIndex(uint8_t index) const {
    if (index < _count) {
        return &_devices[index];
    }
    return nullptr;
}
