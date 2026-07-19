/**
 * health_monitor.h — Monitors memory, wifi status, and runtime health.
 */
#pragma once
#include <Arduino.h>
#include "../communication/transport.h"

struct SystemHealth {
    uint32_t free_memory_bytes;
    bool wifi_connected;
    bool transport_connected;
    uint32_t uptime_seconds;
};

class HealthMonitor {
public:
    HealthMonitor(IAeonTransport& transport);
    void init();

    /** Collects system health metrics. */
    void update(SystemHealth* health);

    /** Print status or send warning logs if critical resources are low. */
    void check();

private:
    IAeonTransport& _transport;
};
