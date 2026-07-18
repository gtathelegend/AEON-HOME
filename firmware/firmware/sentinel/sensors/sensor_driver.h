/**
 * sensor_driver.h — DHT11 and PIR sensor driver.
 */
#pragma once
#include <Arduino.h>

struct SensorReading {
    float temperature;
    float humidity;
    bool  motion;
    bool  door_open;
    float power_draw;
};

class SensorDriver {
public:
    SensorDriver();
    void init();
    void read(SensorReading* reading);
};
