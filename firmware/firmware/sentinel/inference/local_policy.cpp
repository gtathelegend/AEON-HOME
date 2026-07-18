/**
 * local_policy.cpp — Local policy implementation.
 */
#include "local_policy.h"

LocalPolicy::LocalPolicy(ActuatorDriver& actuators, AeonProtocol& protocol)
    : _actuators(actuators), _protocol(protocol),
      _motion_suppressed(false), _temp_suppressed(false) {}

void LocalPolicy::init() {
    _motion_suppressed = false;
    _temp_suppressed = false;
}

void LocalPolicy::evaluate(const SensorReading* reading, AeonState* state) {
    if (!reading || !state) return;

    // 1. Check if false alarm button is pressed
    if (reading->door_open) {
        _actuators.setLed(false);
        if (reading->motion) {
            _motion_suppressed = true;
        }
        if (reading->temperature > state->theta) {
            _temp_suppressed = true;
        }
        // Send notification to backend
        _protocol.sendFeedbackEvent("false_alarm");
        _actuators.playBeep(1);
        return;
    }

    // 2. Reset suppression flags when condition returns to nominal
    if (_motion_suppressed && !reading->motion) {
        _motion_suppressed = false;
    }
    if (_temp_suppressed && (reading->temperature <= state->theta)) {
        _temp_suppressed = false;
    }

    // 3. Simple threshold overlay rule
    bool temp_anomaly = (!_temp_suppressed) && (reading->temperature > state->theta);
    bool comfort_deviation = (reading->temperature > (state->preferred_temp + 3.0f));
    bool motion_active = (!_motion_suppressed) && reading->motion;

    // Turn LED on if alert condition, off otherwise
    _actuators.setLed(temp_anomaly || motion_active || comfort_deviation);
}
