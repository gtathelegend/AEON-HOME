#ifndef AEON_SENSORS_H
#define AEON_SENSORS_H

#include <Arduino.h>

struct SensorReading {
    float temperature;
    float humidity;
    bool  motion;
    bool  door_open;
    float power_draw;
};

// Initialize physical pins (PIR, DHT, etc)
void sensors_init();

// Read raw sensor values into the struct
void sensors_read(SensorReading* reading);

#endif // AEON_SENSORS_H
