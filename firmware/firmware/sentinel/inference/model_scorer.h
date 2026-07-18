/**
 * model_scorer.h — Composite weighted model quality scoring.
 *
 * Computes a single normalized score [0.0, 1.0] from multiple runtime
 * quality signals. All weights are configured in runtime_config.h.
 *
 * Score components:
 *   confidence_component   — current avg confidence (higher = better)
 *   accuracy_component     — training-time accuracy estimate
 *   correction_component   — manual override / correction rate (lower = better)
 *   latency_component      — inference speed (lower latency = better)
 *   reliability_component  — 1 - error_rate (higher = better)
 *   rollback_component     — fewer rollbacks = better
 *   stability_component    — lower confidence variance = better
 *
 * The composite_score is the dot product of component values and weights.
 */
#pragma once
#include <Arduino.h>
#include "statistics_collector.h"
#include "confidence_engine.h"
#include "../storage/runtime_state.h"

struct ModelScoreResult {
    float composite_score;       // Final [0.0, 1.0]
    float confidence_component;
    float accuracy_component;
    float latency_component;
    float reliability_component;
    float stability_component;
    float rollback_component;
    float correction_component;
};

class ModelScorer {
public:
    ModelScorer();

    /**
     * Compute a composite score from runtime stats, confidence report,
     * and a static accuracy estimate from the last deployment.
     *
     * @param stats           Current RuntimeStats from StatisticsCollector
     * @param report          Latest ConfidenceReport
     * @param accuracy_est    Accuracy estimate from training (0.0–1.0)
     * @param correction_rate Manual override rate (0.0–1.0, lower = better)
     * @param model_age_s     Seconds since model activation (for age decay)
     * @return ModelScoreResult
     */
    ModelScoreResult compute(
        const RuntimeStats&     stats,
        const ConfidenceReport& report,
        float accuracy_est,
        float correction_rate,
        uint32_t model_age_s
    ) const;

    /** Persist composite score to AeonState (fixed-point). */
    void persist(const ModelScoreResult& score, AeonState* state) const;

private:
    // Maximum latency where score is 1.0 (any higher → lower score)
    static constexpr float LATENCY_REFERENCE_MS   = 50.0f;
    // Latency at which score hits 0.0
    static constexpr float LATENCY_MAX_MS         = static_cast<float>(ROLLBACK_LATENCY_THRESHOLD);
    // Model age after which age decay starts (seconds)
    static constexpr uint32_t AGE_DECAY_START_S   = 7 * 24 * 3600u;  // 7 days
    // Half-life of age decay (score halves after this many seconds beyond start)
    static constexpr uint32_t AGE_HALF_LIFE_S     = 14 * 24 * 3600u; // 14 days

    static float _normalizeLatency(float avg_latency_ms);
    static float _normalizeRollbacks(uint8_t rollback_count);
    static float _ageDecayFactor(uint32_t model_age_s);
    static float _clamp01(float v);
};
