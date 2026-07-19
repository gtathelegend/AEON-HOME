/**
 * telemetry_manager.cpp — Telemetry manager implementation.
 */
#include "telemetry_manager.h"
#include <string.h>

TelemetryManager::TelemetryManager(SensorDriver &sensors,
                                   FeatureExtractor &features,
                                   AeonProtocol &protocol)
    : _sensors(sensors), _features(features), _protocol(protocol) {
  memset(&_latest_reading, 0, sizeof(_latest_reading));
  memset(&_latest_frame, 0, sizeof(_latest_frame));
}

void TelemetryManager::init() {
  // Subsystems initialized by RuntimeManager
}

void TelemetryManager::transmit(AeonState *state, const char *activity,
                                const char *policy, float confidence) {
  if (!state)
    return;

  // 1. Read physical sensors
  _sensors.read(&_latest_reading);

  // 2. Update statistical features
  _features.update(&_latest_frame, &_latest_reading);

  // 3. Serialize and send update
  _protocol.sendSensorUpdate(&_latest_reading, state->seq, state->model_v,
                             state->profile_version, state->preferred_temp,
                             activity, policy, confidence);
}
