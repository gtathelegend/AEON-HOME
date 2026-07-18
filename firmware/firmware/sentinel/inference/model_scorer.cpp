/**
 * model_scorer.cpp — Composite model quality scorer implementation.
 */
#include "model_scorer.h"
#include <math.h>
#include "../runtime/runtime_config.h"

ModelScorer::ModelScorer() {}

ModelScoreResult ModelScorer::compute(
    const RuntimeStats&     stats,
    const ConfidenceReport& report,
    float accuracy_est,
    float correction_rate,
    uint32_t model_age_s
) const {
    ModelScoreResult r;

    // ── 1. Confidence component ───────────────────────────────────────────────
    r.confidence_component = _clamp01(stats.avg_confidence);

    // ── 2. Accuracy component (training-time estimate) ────────────────────────
    r.accuracy_component = _clamp01(accuracy_est);

    // ── 3. Correction component (lower correction rate = better) ─────────────
    r.correction_component = _clamp01(1.0f - correction_rate);

    // ── 4. Latency component (lower latency = higher score) ───────────────────
    r.latency_component = _normalizeLatency(stats.avg_latency_ms);

    // ── 5. Reliability component (1 - error_rate) ────────────────────────────
    r.reliability_component = _clamp01(1.0f - stats.error_rate);

    // ── 6. Rollback component (fewer rollbacks = better) ─────────────────────
    r.rollback_component = _normalizeRollbacks(stats.rollback_count);

    // ── 7. Stability component (lower variance = better) ─────────────────────
    // Normalize: variance of 0 → 1.0, variance ≥ 0.05 → 0.0
    float norm_var = stats.confidence_variance / 0.05f;
    r.stability_component = _clamp01(1.0f - norm_var);

    // ── Weighted composite ────────────────────────────────────────────────────
    float composite =
        r.confidence_component   * SCORE_W_CONFIDENCE      +
        r.accuracy_component     * SCORE_W_ACCURACY        +
        r.correction_component   * SCORE_W_CORRECTION_RATE +
        r.latency_component      * SCORE_W_LATENCY         +
        r.reliability_component  * SCORE_W_RELIABILITY     +
        r.rollback_component     * SCORE_W_ROLLBACK_HIST   +
        r.stability_component    * SCORE_W_STABILITY;

    // Apply age decay
    float age_factor = _ageDecayFactor(model_age_s);
    composite *= age_factor;

    r.composite_score = _clamp01(composite);
    return r;
}

void ModelScorer::persist(const ModelScoreResult& score, AeonState* state) const {
    if (!state) return;
    uint32_t fp = static_cast<uint32_t>(score.composite_score * 100.0f + 0.5f);
    state->model_score_x100 = static_cast<uint16_t>(fp > 10000u ? 10000u : fp);
}

float ModelScorer::_normalizeLatency(float avg_latency_ms) {
    if (avg_latency_ms <= 0.0f) return 1.0f;  // no data yet
    if (avg_latency_ms <= LATENCY_REFERENCE_MS) return 1.0f;
    if (avg_latency_ms >= LATENCY_MAX_MS) return 0.0f;

    float range = LATENCY_MAX_MS - LATENCY_REFERENCE_MS;
    float over  = avg_latency_ms - LATENCY_REFERENCE_MS;
    return _clamp01(1.0f - (over / range));
}

float ModelScorer::_normalizeRollbacks(uint8_t rollback_count) {
    // 0 rollbacks = 1.0, 5+ rollbacks = 0.0 (linear)
    if (rollback_count == 0) return 1.0f;
    return _clamp01(1.0f - static_cast<float>(rollback_count) / 5.0f);
}

float ModelScorer::_ageDecayFactor(uint32_t model_age_s) {
    if (model_age_s <= AGE_DECAY_START_S) return 1.0f;
    // Exponential decay with half-life = AGE_HALF_LIFE_S
    float t = static_cast<float>(model_age_s - AGE_DECAY_START_S);
    float half_life = static_cast<float>(AGE_HALF_LIFE_S);
    float decay = expf(-0.693147f * t / half_life);
    // Cap minimum age factor at 0.5 (a very old model can still score 50%)
    if (decay < 0.5f) decay = 0.5f;
    return decay;
}

float ModelScorer::_clamp01(float v) {
    if (v < 0.0f) return 0.0f;
    if (v > 1.0f) return 1.0f;
    return v;
}
