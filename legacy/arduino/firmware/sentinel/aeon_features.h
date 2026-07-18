#ifndef AEON_FEATURES_H
#define AEON_FEATURES_H

#include "aeon_sensors.h"

#pragma pack(push, 1)
struct FeatureFrame {
    float temperature;
    float humidity;
    uint8_t motion;
    uint8_t door_open;
    float mean_temp;
    float var_temp;
    float delta_motion;
    uint32_t timestamp_ms;
};
#pragma pack(pop)

void features_init();

// Updates the running statistics and populates the output frame
void features_update(FeatureFrame* frame, const SensorReading* reading);

#endif // AEON_FEATURES_H
