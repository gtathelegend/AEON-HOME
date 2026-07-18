/**
 * confidence_engine.cpp — ConfidenceEngine implementation.
 */
#include "confidence_engine.h"
#include <math.h>

ConfidenceEngine::ConfidenceEngine() {}

ConfidenceReport ConfidenceEngine::evaluate(
    float raw_conf, const RuntimeStats& stats) const
{
    ConfidenceReport report;
    report.raw_confidence = raw_conf;

    // ── Factor 1: Stability (confidence variance penalty) ─────────────────────
    // Higher variance → higher uncertainty → lower adjusted confidence.
    float norm_variance = stats.confidence_variance / HIGH_VARIANCE_THRESHOLD;
    if (norm_variance > 1.0f) norm_variance = 1.0f;
    report.stability_adj = -(norm_variance * MAX_STABILITY_PENALTY);

    // ── Factor 2: Runtime (error rate penalty) ────────────────────────────────
    // High error rate indicates model instability or input issues.
    report.runtime_adj = -(stats.error_rate * MAX_RUNTIME_PENALTY);

    // ── Factor 3: Historical baseline ─────────────────────────────────────────
    // If current confidence is meaningfully above historical avg → small bonus.
    // If well below → small penalty.
    if (stats.total_inferences > 20u) {
        float delta = raw_conf - stats.avg_confidence;
        // Scale: ±0.20 raw difference maps to ±MAX_HISTORICAL_ADJ
        float scaled = delta / 0.20f * MAX_HISTORICAL_ADJ;
        report.historical_adj = _clamp(scaled, -MAX_HISTORICAL_ADJ, MAX_HISTORICAL_ADJ);
    } else {
        report.historical_adj = 0.0f;
    }

    // ── Factor 4: Context (stub, reserved) ────────────────────────────────────
    report.context_adj = 0.0f;

    // ── Final confidence ──────────────────────────────────────────────────────
    float final_val = raw_conf
                    + report.stability_adj
                    + report.runtime_adj
                    + report.historical_adj
                    + report.context_adj;

    report.final_confidence = _clamp(final_val, 0.0f, 1.0f);
    report.category = _categorize(report.final_confidence);

    return report;
}

float ConfidenceEngine::_clamp(float v, float lo, float hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

ConfidenceCategory ConfidenceEngine::_categorize(float v) {
    if (v < CONF_THRESHOLD_LOW)    return CONF_LOW;
    if (v < CONF_THRESHOLD_MEDIUM) return CONF_MEDIUM;
    if (v < CONF_THRESHOLD_HIGH)   return CONF_HIGH;
    return CONF_CRITICAL;
}
