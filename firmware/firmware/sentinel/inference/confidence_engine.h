/**
 * confidence_engine.h — Multi-factor confidence adjustment for on-device inference.
 *
 * Takes the raw scalar output of the inference model and applies four
 * adjustment factors to compute a final, calibrated confidence score:
 *
 *   1. stability_adj  — penalizes high variance in recent confidence values
 *   2. runtime_adj    — penalizes high inference error rate
 *   3. historical_adj — compares running avg to long-term baseline
 *   4. context_adj    — reserved for time-of-day / occupancy context (stub)
 *
 * The final confidence is clamped to [0.0, 1.0].
 * A ConfidenceReport struct captures all intermediate values for telemetry.
 */
#pragma once
#include <Arduino.h>
#include "statistics_collector.h"

// Confidence category thresholds
#define CONF_THRESHOLD_LOW      0.40f
#define CONF_THRESHOLD_MEDIUM   0.65f
#define CONF_THRESHOLD_HIGH     0.85f

enum ConfidenceCategory : uint8_t {
    CONF_LOW      = 0,
    CONF_MEDIUM   = 1,
    CONF_HIGH     = 2,
    CONF_CRITICAL = 3,
};

struct ConfidenceReport {
    float raw_confidence;        // Unmodified model output
    float stability_adj;         // Penalty for high confidence variance (≤ 0)
    float runtime_adj;           // Penalty for high error rate (≤ 0)
    float historical_adj;        // Bonus/penalty vs historical baseline
    float context_adj;           // Stub (reserved)
    float final_confidence;      // Clamped final value [0.0, 1.0]
    ConfidenceCategory category; // Categorical label
};

class ConfidenceEngine {
public:
    ConfidenceEngine();

    /**
     * Compute a calibrated confidence report from a raw inference output.
     *
     * @param raw_conf   Raw scalar output from the model (0.0–1.0)
     * @param stats      Current runtime statistics (variance, error_rate, avg)
     * @return ConfidenceReport with all adjustment factors and final value
     */
    ConfidenceReport evaluate(float raw_conf, const RuntimeStats& stats) const;

private:
    // Maximum stability penalty magnitude (subtracted from confidence)
    static constexpr float MAX_STABILITY_PENALTY  = 0.20f;
    // Maximum runtime (error rate) penalty
    static constexpr float MAX_RUNTIME_PENALTY    = 0.15f;
    // Maximum historical adjustment magnitude (+/-)
    static constexpr float MAX_HISTORICAL_ADJ     = 0.10f;
    // Variance threshold above which full stability penalty is applied
    static constexpr float HIGH_VARIANCE_THRESHOLD = 0.04f; // std ≈ 0.20

    static float _clamp(float v, float lo, float hi);
    static ConfidenceCategory _categorize(float v);
};
