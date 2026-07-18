/**
 * statistics_collector.cpp — Runtime inference statistics implementation.
 */
#include "statistics_collector.h"
#include <math.h>

StatisticsCollector::StatisticsCollector()
    : _conf_m2(0.0f), _conf_mean(0.0f)
{
    reset();
}

void StatisticsCollector::init(const AeonState* state) {
    reset();
    if (state) restore(state);
}

void StatisticsCollector::reset() {
    _stats.total_inferences   = 0;
    _stats.error_count        = 0;
    _stats.avg_confidence     = 0.0f;
    _stats.avg_latency_ms     = 0.0f;
    _stats.min_latency_ms     = 1e6f;   // large sentinel
    _stats.max_latency_ms     = 0.0f;
    _stats.confidence_variance = 0.0f;
    _stats.rollback_count     = 0;
    _stats.error_rate         = 0.0f;
    _conf_m2   = 0.0f;
    _conf_mean = 0.0f;
}

void StatisticsCollector::record(float confidence, float latency_ms, bool success) {
    _stats.total_inferences++;

    if (!success) {
        _stats.error_count++;
        _stats.error_rate = static_cast<float>(_stats.error_count)
                          / static_cast<float>(_stats.total_inferences);
        return;
    }

    // EMA updates
    _stats.avg_confidence = EMA_ALPHA * confidence
                          + (1.0f - EMA_ALPHA) * _stats.avg_confidence;
    _stats.avg_latency_ms = EMA_ALPHA * latency_ms
                          + (1.0f - EMA_ALPHA) * _stats.avg_latency_ms;

    // Latency extremes
    if (latency_ms < _stats.min_latency_ms) _stats.min_latency_ms = latency_ms;
    if (latency_ms > _stats.max_latency_ms) _stats.max_latency_ms = latency_ms;

    // Confidence variance (Welford online)
    _updateVariance(confidence);

    // Error rate
    _stats.error_rate = (_stats.total_inferences > 0)
        ? static_cast<float>(_stats.error_count)
          / static_cast<float>(_stats.total_inferences)
        : 0.0f;
}

void StatisticsCollector::recordRollback() {
    if (_stats.rollback_count < 255u) {
        _stats.rollback_count++;
    }
}

void StatisticsCollector::persist(AeonState* state) const {
    if (!state) return;

    state->inference_count = _stats.total_inferences;

    // Fixed-point encode: multiply by 100, clamp to uint16_t range
    uint32_t conf_fp = static_cast<uint32_t>(_stats.avg_confidence * 100.0f + 0.5f);
    state->avg_confidence_x100 = static_cast<uint16_t>(conf_fp > 10000u ? 10000u : conf_fp);

    uint32_t lat_fp = static_cast<uint32_t>(_stats.avg_latency_ms + 0.5f);
    state->avg_latency_ms = static_cast<uint16_t>(lat_fp > 65535u ? 65535u : lat_fp);

    uint32_t err_fp = (_stats.error_count > 65535u) ? 65535u : _stats.error_count;
    state->error_count = static_cast<uint16_t>(err_fp);

    state->rollback_count = _stats.rollback_count;
}

void StatisticsCollector::restore(const AeonState* state) {
    if (!state) return;

    _stats.total_inferences  = state->inference_count;
    _stats.avg_confidence    = static_cast<float>(state->avg_confidence_x100) / 100.0f;
    _stats.avg_latency_ms    = static_cast<float>(state->avg_latency_ms);
    _stats.error_count       = state->error_count;
    _stats.rollback_count    = state->rollback_count;
    _stats.error_rate        = (_stats.total_inferences > 0)
        ? static_cast<float>(_stats.error_count)
          / static_cast<float>(_stats.total_inferences)
        : 0.0f;

    // Seed EMA means from restored values
    _conf_mean = _stats.avg_confidence;
}

void StatisticsCollector::_updateVariance(float new_val) {
    // Welford online variance — numerically stable
    float n    = static_cast<float>(_stats.total_inferences);
    float delta = new_val - _conf_mean;
    _conf_mean += delta / n;
    float delta2 = new_val - _conf_mean;
    _conf_m2   += delta * delta2;

    if (n > 1.0f) {
        _stats.confidence_variance = _conf_m2 / (n - 1.0f);
    }
}
