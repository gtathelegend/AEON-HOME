#include "health_monitor.h"
#include <Arduino.h>

#if defined(ARDUINO_UNOWIFIR4)
#include <WiFiS3.h>
#elif !defined(ARDUINO_UNO_Q)
#include <WiFi.h>
#endif

#if defined(ARDUINO_ARCH_AVR)
extern int __bss_end;
extern void *__brkval;
int getFreeMemory() {
    int free_memory;
    if ((int)__brkval == 0) {
        free_memory = ((int)&free_memory) - ((int)&__bss_end);
    } else {
        free_memory = ((int)&free_memory) - ((int)__brkval);
    }
    return free_memory;
}
#elif (defined(ARDUINO_ARCH_STM32) || defined(ARDUINO_ARCH_STM32F4) || defined(ARDUINO_ARCH_STM32L4) || defined(ARDUINO_UNOWIFIR4) || defined(__arm__)) && !defined(ARDUINO_UNO_Q)
extern "C" char* sbrk(int incr);
int getFreeMemory() {
    char top;
    return &top - sbrk(0);
}
#else
int getFreeMemory() {
    return 16384; // default dummy fallback for unsupported architectures
}
#endif

HealthMonitor::HealthMonitor(IAeonTransport& transport)
    : _transport(transport) {}

void HealthMonitor::init() {}

void HealthMonitor::update(SystemHealth* health) {
    if (!health) return;

    health->free_memory_bytes = getFreeMemory();
#if defined(ARDUINO_UNO_Q)
    health->wifi_connected = _transport.isConnected();
#else
    health->wifi_connected = (WiFi.status() == WL_CONNECTED);
#endif
    health->transport_connected = _transport.isConnected();
    health->uptime_seconds = millis() / 1000;
}

void HealthMonitor::check() {
    SystemHealth health;
    update(&health);

    // If memory runs critically low, print debug warning
    if (health.free_memory_bytes < 512) {
        Serial.print("[HEALTH] WARNING: Memory low: ");
        Serial.println(health.free_memory_bytes);
    }
}
