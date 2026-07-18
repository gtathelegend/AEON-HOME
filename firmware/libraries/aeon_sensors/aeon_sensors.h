/**
 * aeon_sensors.h — Sensor abstraction layer.
 *
 * Supported sensors (pin mapping):
 *   - DHT11 (temperature + humidity) on pin 2
 *   - HC-SR501 PIR (motion)          on pin 3
 *   - Button (false alarm / reed)    on pin 4
 */

#pragma once
#include <stdint.h>

typedef struct {
  float    temperature;   // °C, NaN if read failed
  float    humidity;      // %, NaN if read failed
  uint8_t  motion;        // 1 = motion present
  uint8_t  door_open;     // 1 = door open
  uint32_t timestamp_ms;
} SensorReading;

/** Initialise sensor pins and libraries. Call once in setup(). */
void sensors_init(void);

/** Populate a SensorReading with the latest values. */
void sensors_read(SensorReading* out);
