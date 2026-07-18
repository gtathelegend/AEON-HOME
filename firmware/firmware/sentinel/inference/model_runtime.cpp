/**
 * model_runtime.cpp — Full model runtime implementation.
 */
#include "model_runtime.h"
#include <math.h>
#include <string.h>
#include "../runtime/runtime_config.h"

ModelRuntime::ModelRuntime()
    : _correction_rate(0.0f)
{}

void ModelRuntime::init(const AeonState* state) {
    _stats.init(state);
    _learning_buf.init(state);
    _correction_rate = 0.0f;

    if (state && state->model_v > 0) {
        _active.version    = state->model_v;
        _active.mean       = state->mean;
        _active.std_dev    = (state->std_dev > 0.001f) ? state->std_dev : 1.0f;
        _active.theta      = state->theta;
        _active.valid      = true;
    } else {
        _active.version    = DEFAULT_MODEL_V;
        _active.mean       = DEFAULT_MEAN;
        _active.std_dev    = DEFAULT_STD_DEV > 0.001f ? DEFAULT_STD_DEV : 1.0f;
        _active.theta      = DEFAULT_THETA;
        _active.valid      = true;
    }

    _previous  = {};
    _candidate = {};
}

// ── Deployment lifecycle ─────────────────────────────────────────────────────

void ModelRuntime::loadDeployment(
    const DeploymentManifest& manifest, AeonState* state)
{
    _candidate.version      = manifest.model_version;
    _candidate.mean         = manifest.mean;
    _candidate.std_dev      = (manifest.std_dev > 0.001f) ? manifest.std_dev : 1.0f;
    _candidate.theta        = manifest.theta;
    _candidate.accuracy_est = manifest.accuracy_estimate;
    _candidate.valid        = true;

    if (state) {
        state->deployment_id = manifest.deployment_id;
    }

    Serial.print("[ModelRuntime] Candidate loaded: v");
    Serial.println(manifest.model_version);
}

void ModelRuntime::activateCandidate(AeonState* state) {
    if (!_candidate.valid) {
        Serial.println("[ModelRuntime] No candidate to activate.");
        return;
    }

    _previous = _active;   // promote active → previous (rollback target)
    _active   = _candidate; // promote candidate → active
    _candidate = {};

    // Reset statistics for the new model
    _stats.reset();
    _correction_rate = 0.0f;

    _applyParamsToState(_active, state);
    Serial.print("[ModelRuntime] Activated v");
    Serial.println(_active.version);
}

void ModelRuntime::rollbackToPrevious(AeonState* state) {
    if (!_previous.valid) {
        Serial.println("[ModelRuntime] No previous model for rollback.");
        return;
    }

    _candidate = {};
    _active    = _previous;
    _previous  = {};

    _stats.recordRollback();
    _stats.reset();

    _applyParamsToState(_active, state);
    Serial.print("[ModelRuntime] Rolled back to v");
    Serial.println(_active.version);
}

// ── Inference ────────────────────────────────────────────────────────────────

InferenceResult ModelRuntime::executeInference(
    float temperature, uint32_t /*seq*/, uint32_t /*ts_ms*/)
{
    InferenceResult result;
    uint32_t start = millis();

    // Input validation
    if (temperature < -40.0f || temperature > 125.0f || !_active.valid) {
        result.success    = false;
        result.prediction = 0;
        result.raw_score  = 0.0f;
        result.latency_ms = millis() - start;
        _stats.record(0.0f, static_cast<float>(result.latency_ms), false);
        return result;
    }

    // Z-score anomaly detection
    float z = _zScore(temperature);
    float sigmoid_raw = _sigmoid(z - _active.theta);

    result.raw_score  = z;
    result.prediction = (z > _active.theta) ? 1 : 0;
    result.latency_ms = millis() - start;
    result.success    = true;

    // Confidence adjustment via ConfidenceEngine
    result.confidence = _confidence_engine.evaluate(sigmoid_raw, _stats.getStats());

    // Record in statistics
    _stats.record(
        result.confidence.final_confidence,
        static_cast<float>(result.latency_ms),
        true
    );

    return result;
}

void ModelRuntime::recordForLearning(
    const InferenceResult& result,
    const float* feature_vector,
    uint32_t seq,
    uint32_t ts_ms,
    bool manual_override
) {
    LearningRecord rec;
    rec.timestamp_ms    = ts_ms;
    rec.seq             = seq;
    rec.prediction      = result.prediction;
    rec.confidence_x100 = static_cast<uint16_t>(
        result.confidence.final_confidence * 100.0f + 0.5f);
    rec.manual_override = manual_override;

    for (uint8_t i = 0; i < FEATURE_VECTOR_LEN; i++) {
        rec.features[i] = (feature_vector) ? feature_vector[i] : 0.0f;
    }

    _learning_buf.append(rec);

    if (manual_override) {
        // Update correction rate using EMA
        _correction_rate = 0.05f * 1.0f + 0.95f * _correction_rate;
    } else {
        _correction_rate = 0.05f * 0.0f + 0.95f * _correction_rate;
    }
}

// ── Legacy API ───────────────────────────────────────────────────────────────

void ModelRuntime::updateModel(
    uint32_t version, float mean, float std_dev, float theta, AeonState* state)
{
    // Backward-compatible: directly update active parameters
    _previous = _active;
    _active.version = version;
    _active.mean    = mean;
    _active.std_dev = (std_dev > 0.001f) ? std_dev : 1.0f;
    _active.theta   = theta;
    _active.valid   = true;
    _stats.reset();
    _applyParamsToState(_active, state);
}

uint32_t ModelRuntime::getVersion(const AeonState* state) const {
    return state ? state->model_v : _active.version;
}
float ModelRuntime::getMean(const AeonState* state) const {
    return state ? state->mean : _active.mean;
}
float ModelRuntime::getStdDev(const AeonState* state) const {
    return state ? state->std_dev : _active.std_dev;
}
float ModelRuntime::getTheta(const AeonState* state) const {
    return state ? state->theta : _active.theta;
}

// ── Score & Persistence ───────────────────────────────────────────────────────

ModelScoreResult ModelRuntime::computeScore(uint32_t model_age_s) const {
    // Build a dummy confidence report from current stats for scorer input
    ConfidenceReport cr;
    cr.raw_confidence   = _stats.getStats().avg_confidence;
    cr.final_confidence = _stats.getStats().avg_confidence;
    cr.stability_adj    = 0.0f;
    cr.runtime_adj      = 0.0f;
    cr.historical_adj   = 0.0f;
    cr.context_adj      = 0.0f;
    cr.category         = CONF_MEDIUM;

    return _scorer.compute(
        _stats.getStats(),
        cr,
        _active.accuracy_est,
        _correction_rate,
        model_age_s
    );
}

void ModelRuntime::persistStats(AeonState* state) {
    _stats.persist(state);
    ModelScoreResult score = computeScore(0);
    _scorer.persist(score, state);
    _learning_buf.persist(state);
}

// ── Private helpers ───────────────────────────────────────────────────────────

float ModelRuntime::_zScore(float temperature) const {
    if (_active.std_dev < 0.001f) return 0.0f;
    float diff = temperature - _active.mean;
    if (diff < 0.0f) diff = -diff;
    return diff / _active.std_dev;
}

float ModelRuntime::_sigmoid(float x) const {
    return 1.0f / (1.0f + expf(-x));
}

void ModelRuntime::_applyParamsToState(const ModelParams& p, AeonState* state) {
    if (!state) return;
    state->model_v  = p.version;
    state->mean     = p.mean;
    state->std_dev  = p.std_dev;
    state->theta    = p.theta;
}
