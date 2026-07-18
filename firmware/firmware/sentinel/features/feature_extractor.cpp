/**
 * feature_extractor.cpp — Statistical feature extractor implementation.
 */
#include "feature_extractor.h"

FeatureExtractor::FeatureExtractor()
    : _idx(0), _filled(false) {}

void FeatureExtractor::init() {
    for (int i = 0; i < FEATURE_WINDOW_SIZE; i++) {
        _temp_history[i] = 0.0f;
        _motion_history[i] = 0;
    }
    _idx = 0;
    _filled = false;
}

void FeatureExtractor::update(FeatureFrame* frame, const SensorReading* reading) {
    if (!frame || !reading) return;

    frame->temperature  = reading->temperature;
    frame->humidity     = reading->humidity;
    frame->motion       = reading->motion ? 1 : 0;
    frame->door_open    = reading->door_open ? 1 : 0;
    frame->timestamp_ms = millis();

    _temp_history[_idx]   = reading->temperature;
    _motion_history[_idx] = frame->motion;
    _idx++;
    if (_idx >= FEATURE_WINDOW_SIZE) {
        _idx = 0;
        _filled = true;
    }

    int count = _filled ? FEATURE_WINDOW_SIZE : (_idx == 0 ? 1 : _idx);
    float sum_temp = 0.0f;
    float sum_motion = 0.0f;

    for (int i = 0; i < count; i++) {
        sum_temp += _temp_history[i];
        sum_motion += _motion_history[i];
    }
    frame->mean_temp = sum_temp / count;

    float var_temp = 0.0f;
    for (int i = 0; i < count; i++) {
        float diff = _temp_history[i] - frame->mean_temp;
        var_temp += (diff * diff);
    }
    frame->var_temp = var_temp / count;

    // Delta motion (average motion over window)
    frame->delta_motion = sum_motion / count;
}
