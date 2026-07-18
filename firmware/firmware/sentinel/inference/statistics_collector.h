/**
 * statistics_collector.h — Tracks runtime inference statistics on-device.
 *
 * Accumulates per-inference measurements and persists summary statistics
 * to AeonState for flash survival across reboots. Uses fixed-point arithmetic
 * to avoid floating-point in flash layout (consistent with AeonState encoding).
 *
 * All statistics are computed as exponential moving averages to bound memory.
 */
#pragma once
#include <Arduino.h>
#include "../storage/runtime_state.h"
#include "../runtime/runtime_config.h"

struct RuntimeStats {
    uint32_t total_inferences;   // All calls to executeInference()
    uint32_t error_count;        // Failed / exceptional inferences
    float    avg_confidence;     // EMA of raw confidence values
    float    avg_latency_ms;     // EMA of inference latency in ms
    float    min_latency_ms;     // Lifetime minimum (resets on model change)
    float    max_latency_ms;     // Lifetime maximum
    float    confidence_variance; // Variance of recent confidence (stability proxy)
    uint8_t  rollback_count;     // Rollbacks attributed to this model version
    float    error_rate;         // error_count / total_inferences (0.0–1.0)
};

class StatisticsCollector {
public:
    StatisticsCollector();

    /** Initialize and restore from persisted AeonState. */
    void init(const AeonState* state);

    /** Record one inference result. Called after every inference attempt. */
    void record(float confidence, float latency_ms, bool success);

    /** Record a firmware-side rollback event. */
    void recordRollback();

    /** Flush summary to AeonState fields for flash persistence. */
    void persist(AeonState* state) const;

    /** Restore from AeonState after reboot. */
    void restore(const AeonState* state);

    /** Reset all statistics (called on model change/activation). */
    void reset();

    /** Read-only snapshot of current statistics. */
    const RuntimeStats& getStats() const { return _stats; }

private:
    RuntimeStats _stats;

    // EMA smoothing factor α = 2 / (N + 1), where N is window size
    static constexpr float EMA_ALPHA = 0.10f;   // ~19-sample window

    // Confidence variance accumulator (Welford online algorithm)
    float _conf_m2;    // Sum of squared deviations (for variance)
    float _conf_mean;  // Running mean for variance computation

    void _updateVariance(float new_val);
};
