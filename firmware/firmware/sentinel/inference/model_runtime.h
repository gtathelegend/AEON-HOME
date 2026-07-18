/**
 * model_runtime.h — On-device model runtime with full deployment lifecycle.
 *
 * Replaces the previous minimal 4-field runtime with a complete lifecycle:
 *
 *   - Maintains Active and Previous model parameter sets
 *   - Accepts deployment manifests from the backend (via command router)
 *   - Executes on-device inference (statistical z-score anomaly model)
 *   - Delegates confidence adjustment to ConfidenceEngine
 *   - Delegates composite scoring to ModelScorer
 *   - Persists relevant state to AeonState via StatisticsCollector
 *
 * The inference model is a z-score anomaly detector:
 *   score(x) = |x - mean| / std_dev
 *   prediction = 1 (anomaly) if score > theta
 *   confidence = sigmoid(score) mapped to [0, 1]
 *
 * This matches the model parameters updated by `model_update` commands
 * from the backend trainer.
 */
#pragma once
#include <Arduino.h>
#include "../storage/runtime_state.h"
#include "statistics_collector.h"
#include "confidence_engine.h"
#include "model_scorer.h"
#include "learning_buffer.h"

// Deployment manifest passed from CommandRouter when backend pushes a model
struct DeploymentManifest {
    uint32_t deployment_id;      // Numeric deployment ID (from AeonState)
    uint32_t model_version;      // Semantic version integer
    float    mean;               // Temperature mean for anomaly scoring
    float    std_dev;            // Temperature std dev
    float    theta;              // Decision threshold
    float    accuracy_estimate;  // Training-time accuracy (0.0–1.0)
    char     checksum[65];       // SHA-256 hex string (64 chars + null)
};

// Snapshot of a single inference result
struct InferenceResult {
    uint8_t          prediction;    // 0 = normal, 1 = anomaly
    ConfidenceReport confidence;    // Full confidence report
    float            raw_score;     // Z-score before thresholding
    uint32_t         latency_ms;    // Wall-clock inference duration
    bool             success;       // False on input validation failure
};

class ModelRuntime {
public:
    ModelRuntime();

    /** Initialize subsystems and restore from persisted AeonState. */
    void init(const AeonState* state = nullptr);

    // ── Deployment lifecycle ──────────────────────────────────────────────────

    /**
     * Load a new deployment manifest as a candidate.
     * Does NOT activate — call activateCandidate() to commit.
     *
     * @param manifest  Deployment parameters from the backend
     * @param state     Mutable AeonState to update deployment_id
     */
    void loadDeployment(const DeploymentManifest& manifest, AeonState* state);

    /**
     * Activate the staged candidate as the active model.
     * Promotes current active to previous (rollback target).
     */
    void activateCandidate(AeonState* state);

    /**
     * Roll back to the previous model parameters.
     * Called by RollbackManager on automatic rollback.
     */
    void rollbackToPrevious(AeonState* state);

    // ── Inference ─────────────────────────────────────────────────────────────

    /**
     * Execute on-device inference using the active model parameters.
     *
     * @param temperature  Raw temperature reading (°C)
     * @param seq          Current frame sequence number
     * @param ts_ms        Current millis() timestamp
     * @return             InferenceResult with prediction, confidence, latency
     */
    InferenceResult executeInference(float temperature, uint32_t seq, uint32_t ts_ms);

    /**
     * Append the latest inference to the learning buffer (with override flag).
     * Call this after every inference, and additionally when a user correction
     * is received.
     */
    void recordForLearning(
        const InferenceResult& result,
        const float* feature_vector,
        uint32_t seq,
        uint32_t ts_ms,
        bool manual_override
    );

    // ── Legacy API (backward compatibility with existing command router) ───────

    /** Apply model parameters from a model_update command (backward compat). */
    void updateModel(uint32_t version, float mean, float std_dev,
                     float theta, AeonState* state);

    uint32_t getVersion(const AeonState* state) const;
    float getMean(const AeonState* state) const;
    float getStdDev(const AeonState* state) const;
    float getTheta(const AeonState* state) const;

    // ── Statistics & Scoring access ───────────────────────────────────────────

    const StatisticsCollector& statistics() const { return _stats; }
    StatisticsCollector&       statistics()       { return _stats; }
    LearningBuffer&            learningBuffer()   { return _learning_buf; }

    /** Compute and return the latest composite model score. */
    ModelScoreResult computeScore(uint32_t model_age_s = 0) const;

    /** Persist runtime stats and score to AeonState. */
    void persistStats(AeonState* state);

private:
    // Active model parameters (the model currently executing inference)
    struct ModelParams {
        uint32_t version       = 0;
        float    mean          = 0.0f;
        float    std_dev       = 1.0f;
        float    theta         = DEFAULT_THETA;
        float    accuracy_est  = 0.0f;
        bool     valid         = false;
    };

    ModelParams _active;      // Currently running model
    ModelParams _previous;    // Rollback target
    ModelParams _candidate;   // Staged, not yet committed

    StatisticsCollector _stats;
    ConfidenceEngine    _confidence_engine;
    ModelScorer         _scorer;
    LearningBuffer      _learning_buf;

    float _correction_rate;   // Tracks manual override frequency

    // Internal inference helpers
    float _zScore(float temperature) const;
    float _sigmoid(float x) const;
    void  _applyParamsToState(const ModelParams& p, AeonState* state);
};
