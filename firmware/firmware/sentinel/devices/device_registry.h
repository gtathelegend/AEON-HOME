/**
 * device_registry.h — Local device registry runtime.
 */
#pragma once
#include <Arduino.h>

struct DeviceRecord {
    char id[16];
    char type[16];
    char version[8];
    bool online;
    unsigned long last_seen_ms;
    int rssi;
};

class DeviceRegistry {
public:
    DeviceRegistry();
    void init();

    /** Register or update a device record. */
    bool registerDevice(const char* id, const char* type, const char* version);

    /** Update online status and RSSI. */
    void updateLiveness(const char* id, int rssi);

    /** Periodic cleanup task — marks unresponsive devices offline. */
    void pollLiveness(unsigned long timeout_ms);

    uint8_t getDeviceCount() const { return _count; }
    const DeviceRecord* getDeviceByIndex(uint8_t index) const;

private:
    static const uint8_t MAX_DEVICES = 4;
    DeviceRecord _devices[MAX_DEVICES];
    uint8_t _count;
};
