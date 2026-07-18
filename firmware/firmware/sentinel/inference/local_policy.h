/**
 * local_policy.h — On-device policy execution and button feedback.
 */
#pragma once
#include "../sensors/sensor_driver.h"
#include "../actuators/actuator_driver.h"
#include "../protocols/aeon_protocol.h"
#include "../storage/runtime_state.h"

class LocalPolicy {
public:
    LocalPolicy(ActuatorDriver& actuators, AeonProtocol& protocol);
    void init();

    /** Run policy check. Evaluates sensors and applies local rules (e.g. alarm suppression). */
    void evaluate(const SensorReading* reading, AeonState* state);

    void setSuppressed(bool motion, bool temp) {
        _motion_suppressed = motion;
        _temp_suppressed = temp;
    }

private:
    ActuatorDriver& _actuators;
    AeonProtocol&   _protocol;

    bool _motion_suppressed;
    bool _temp_suppressed;
};
