/**
 * model_runtime.h — Tracks active model configuration and parameters.
 */
#pragma once
#include <Arduino.h>
#include "../storage/runtime_state.h"

class ModelRuntime {
public:
    ModelRuntime();
    void init();

    /** Apply parameters from a model update command. */
    void updateModel(uint32_t version, float mean, float std_dev, float theta, AeonState* state);

    uint32_t getVersion(const AeonState* state) const;
    float getMean(const AeonState* state) const;
    float getStdDev(const AeonState* state) const;
    float getTheta(const AeonState* state) const;
};
