/**
 * aeon_sensors.cpp — Sensor read implementation.
 *
 * Depends on:
 *   - DHT sensor library  (temperature + humidity)
 *   - Standard Arduino digital I/O (PIR, door reed switch)
 */

#include "aeon_sensors.h"
#include <Arduino.h>
#include <DHT.h>
#include <math.h>

#define PIN_DHT11   2
#define PIN_PIR     3
#define PIN_BUTTON  4
#define DHT_TYPE    DHT11

static DHT dht(PIN_DHT11, DHT_TYPE);

void sensors_init(void) {
  dht.begin();
  pinMode(PIN_PIR,    INPUT);
  pinMode(PIN_BUTTON, INPUT_PULLUP);   // LOW = pressed
}

void sensors_read(SensorReading* out) {
  out->timestamp_ms = millis();
  out->temperature  = dht.readTemperature();
  out->humidity     = dht.readHumidity();
  out->motion       = (uint8_t)digitalRead(PIN_PIR);
  out->door_open    = (uint8_t)(!digitalRead(PIN_DOOR));  // active-low

  // Replace NaN with sentinel (Snapdragon will handle)
  if (isnan(out->temperature)) out->temperature = -999.0f;
  if (isnan(out->humidity))    out->humidity    = -999.0f;
}
