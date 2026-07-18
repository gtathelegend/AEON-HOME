/**
 * rollback_manager.cpp — Automatic runtime rollback trigger implementation.
 */
#include "rollback_manager.h"
#include "model_runtime.h"
#include "../protocols/aeon_protocol.h"
#include "../checkpoint/checkpoint_manager.h"
#include "../runtime/runtime_config.h"

RollbackManager::RollbackManager(
    ModelRuntime&      model_runtime,
    AeonProtocol&      protocol,
    CheckpointManager& checkpoint
)
    : _model_runtime(model_runtime),
      _protocol(protocol),
      _checkpoint(checkpoint),
      _is_rolled_back(false)
{}

void RollbackManager::reset() {
    _is_rolled_back = false;
}

RollbackTrigger RollbackManager::evaluate(
    const RuntimeStats&     stats,
    const ModelScoreResult& score,
    AeonState*              state
) {
    // Already rolled back — do not re-evaluate until a new model is activated
    if (_is_rolled_back) return ROLLBACK_NONE;

    // Only evaluate if we have meaningful inference history (at least 50 inferences)
    if (stats.total_inferences < 50u) return ROLLBACK_NONE;

    // ── Check 1: Composite score ──────────────────────────────────────────────
    if (score.composite_score < ROLLBACK_SCORE_THRESHOLD) {
        _executeRollback(ROLLBACK_LOW_SCORE, state);
        return ROLLBACK_LOW_SCORE;
    }

    // ── Check 2: Average confidence ───────────────────────────────────────────
    if (stats.avg_confidence < ROLLBACK_CONF_THRESHOLD) {
        _executeRollback(ROLLBACK_LOW_CONFIDENCE, state);
        return ROLLBACK_LOW_CONFIDENCE;
    }

    // ── Check 3: Average latency ──────────────────────────────────────────────
    if (stats.avg_latency_ms > static_cast<float>(ROLLBACK_LATENCY_THRESHOLD)) {
        _executeRollback(ROLLBACK_HIGH_LATENCY, state);
        return ROLLBACK_HIGH_LATENCY;
    }

    // ── Check 4: Error rate ───────────────────────────────────────────────────
    if (stats.error_rate > ROLLBACK_ERROR_RATE_THRESHOLD) {
        _executeRollback(ROLLBACK_HIGH_ERROR_RATE, state);
        return ROLLBACK_HIGH_ERROR_RATE;
    }

    return ROLLBACK_NONE;
}

void RollbackManager::_executeRollback(RollbackTrigger trigger, AeonState* state) {
    Serial.print("[ROLLBACK] Trigger: ");
    Serial.println(_triggerName(trigger));

    _is_rolled_back = true;

    // Restore previous model parameters in ModelRuntime
    _model_runtime.rollbackToPrevious(state);

    // Notify backend
    _protocol.sendModelRolledBack(
        state ? state->model_v : 0,
        _triggerName(trigger)
    );

    // Persist clean state after rollback
    if (state) {
        _checkpoint.save(state);
    }

    Serial.println("[ROLLBACK] Completed. Previous model restored.");
}

const char* RollbackManager::_triggerName(RollbackTrigger t) {
    switch (t) {
        case ROLLBACK_LOW_SCORE:       return "low_score";
        case ROLLBACK_LOW_CONFIDENCE:  return "low_confidence";
        case ROLLBACK_HIGH_LATENCY:    return "high_latency";
        case ROLLBACK_HIGH_ERROR_RATE: return "high_error_rate";
        default:                       return "none";
    }
}
