/**
 * sensor_driver.cpp — Sensor driver implementation.
 */
#include "sensor_driver.h"
#include "../runtime/runtime_config.h"
#include <DHT.h>

static DHT dht(PIN_DHT, DHT_TYPE);

SensorDriver::SensorDriver() {}

void SensorDriver::init() {
    dht.begin();
    pinMode(PIN_PIR, INPUT);
    pinMode(PIN_BUTTON, INPUT_PULLUP);
}

void SensorDriver::read(SensorReading* reading) {
    if (!reading) return;

    reading->temperature = dht.readTemperature();
    reading->humidity    = dht.readHumidity();
    reading->motion      = (digitalRead(PIN_PIR) == HIGH);
    reading->door_open   = (digitalRead(PIN_BUTTON) == LOW); // LOW when button pressed

    if (isnan(reading->temperature)) reading->temperature = -999.0f;
    if (isnan(reading->humidity))    reading->humidity    = -999.0f;
    reading->power_draw  = 12.5f; // estimated nominal draw
}
