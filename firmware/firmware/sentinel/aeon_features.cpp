#include "aeon_features.h"

#define WINDOW_SIZE 10

static float s_temp_history[WINDOW_SIZE];
static uint8_t s_motion_history[WINDOW_SIZE];
static uint8_t s_idx = 0;
static bool s_filled = false;

void features_init() {
    for (int i = 0; i < WINDOW_SIZE; i++) {
        s_temp_history[i] = 0.0f;
        s_motion_history[i] = 0;
    }
    s_idx = 0;
    s_filled = false;
}

void features_update(FeatureFrame* frame, const SensorReading* reading) {
    if (!frame || !reading) return;
    
    // Copy base values
    frame->temperature  = reading->temperature;
    frame->humidity     = reading->humidity;
    frame->motion       = reading->motion ? 1 : 0;
    frame->door_open    = reading->door_open ? 1 : 0;
    frame->timestamp_ms = millis();
    
    // Update history
    s_temp_history[s_idx]   = reading->temperature;
    s_motion_history[s_idx] = frame->motion;
    s_idx++;
    if (s_idx >= WINDOW_SIZE) {
        s_idx = 0;
        s_filled = true;
    }
    
    // Calculate mean & var
    int count = s_filled ? WINDOW_SIZE : (s_idx == 0 ? 1 : s_idx);
    float sum_temp = 0.0f;
    float sum_motion = 0.0f;
    
    for (int i = 0; i < count; i++) {
        sum_temp += s_temp_history[i];
        sum_motion += s_motion_history[i];
    }
    frame->mean_temp = sum_temp / count;
    
    float var_temp = 0.0f;
    for (int i = 0; i < count; i++) {
        float diff = s_temp_history[i] - frame->mean_temp;
        var_temp += (diff * diff);
    }
    frame->var_temp = var_temp / count;
    
    // Delta motion (average motion over window)
    frame->delta_motion = sum_motion / count;
}
