#ifndef AEON_POLICY_H
#define AEON_POLICY_H

#include <Arduino.h>
#include "aeon_sensors.h"
#include "aeon_checkpoint.h"

// Process an incoming JSON command (policy_update, model_update, etc.)
void policy_update(const char* json_str, AeonState* state);

// Execute a policy locally (called when AI is offline or simple trigger)
void policy_evaluate(const SensorReading* reading);

#endif // AEON_POLICY_H
