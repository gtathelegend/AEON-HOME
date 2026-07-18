/**
 * feature_extractor.h — Statistical features extractor.
 */
#pragma once
#include "../sensors/sensor_driver.h"
#include "../runtime/runtime_config.h"

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

class FeatureExtractor {
public:
    FeatureExtractor();
    void init();
    void update(FeatureFrame* frame, const SensorReading* reading);

private:
    float _temp_history[FEATURE_WINDOW_SIZE];
    uint8_t _motion_history[FEATURE_WINDOW_SIZE];
    uint8_t _idx;
    bool _filled;
};
