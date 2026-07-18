/**
 * aeon_features.h — Lightweight on-device feature extraction.
 *
 * Computes rolling statistics over a sliding window of sensor readings.
 * These features are what gets sent to the Snapdragon, never raw readings.
 *
 * Features per channel:
 *   mean, variance, min, max, delta (last-to-current difference)
 *
 * Window size: FEATURE_WINDOW (default 10 samples = 5 s at 500 ms/sample)
 */

#pragma once
#include "aeon_sensors.h"
#include "aeon_protocol.h"

#define FEATURE_WINDOW 10

/** Initialise feature extraction state. Call once in setup(). */
void features_init(void);

/**
 * Ingest one SensorReading and update the FeatureFrame.
 * Call after every sensors_read().
 */
void features_update(FeatureFrame* frame, const SensorReading* reading);
