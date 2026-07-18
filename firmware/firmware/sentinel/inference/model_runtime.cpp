/**
 * model_runtime.cpp — Model runtime implementation.
 */
#include "model_runtime.h"

ModelRuntime::ModelRuntime() {}

void ModelRuntime::init() {}

void ModelRuntime::updateModel(uint32_t version, float mean, float std_dev, float theta, AeonState* state) {
    if (!state) return;
    state->model_v = version;
    state->mean = mean;
    state->std_dev = std_dev;
    state->theta = theta;
}

uint32_t ModelRuntime::getVersion(const AeonState* state) const {
    return state ? state->model_v : 1;
}

float ModelRuntime::getMean(const AeonState* state) const {
    return state ? state->mean : 0.0f;
}

float ModelRuntime::getStdDev(const AeonState* state) const {
    return state ? state->std_dev : 1.0f;
}

float ModelRuntime::getTheta(const AeonState* state) const {
    return state ? state->theta : 25.0f;
}
