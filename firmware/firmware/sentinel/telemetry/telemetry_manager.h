/**
 * telemetry_manager.h — Aggregates and sends sensor/telemetry updates.
 */
#pragma once
#include "../sensors/sensor_driver.h"
#include "../features/feature_extractor.h"
#include "../protocols/aeon_protocol.h"
#include "../storage/runtime_state.h"

class TelemetryManager {
public:
    TelemetryManager(SensorDriver& sensors, FeatureExtractor& features, AeonProtocol& protocol);
    void init();

    /** Read sensors, extract features, send update to transport. */
    void transmit(AeonState* state);

    const SensorReading* getLatestReading() const { return &_latest_reading; }
    const FeatureFrame* getLatestFrame() const { return &_latest_frame; }

private:
    SensorDriver&     _sensors;
    FeatureExtractor& _features;
    AeonProtocol&     _protocol;

    SensorReading     _latest_reading;
    FeatureFrame      _latest_frame;
};
