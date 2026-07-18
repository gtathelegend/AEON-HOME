/**
 * rollback_manager.h — Automatic runtime rollback trigger.
 *
 * Monitors runtime health on every statistics flush tick and decides
 * whether the active model should be rolled back based on configurable
 * thresholds (all defined in runtime_config.h).
 *
 * Rollback conditions (ANY of these triggers a rollback):
 *   1. Composite model score < ROLLBACK_SCORE_THRESHOLD
 *   2. Average confidence < ROLLBACK_CONF_THRESHOLD
 *   3. Average latency > ROLLBACK_LATENCY_THRESHOLD (ms)
 *   4. Error rate > ROLLBACK_ERROR_RATE_THRESHOLD
 *
 * On rollback:
 *   - Calls ModelRuntime::rollbackToPrevious()
 *   - Records a rollback in StatisticsCollector
 *   - Sends a ModelRolledBack protocol message
 *   - Saves a checkpoint
 */
#pragma once
#include <Arduino.h>
#include "statistics_collector.h"
#include "model_scorer.h"
#include "../storage/runtime_state.h"

// Forward declarations
class ModelRuntime;
class AeonProtocol;
class CheckpointManager;

enum RollbackTrigger : uint8_t {
    ROLLBACK_NONE            = 0,
    ROLLBACK_LOW_SCORE       = 1,
    ROLLBACK_LOW_CONFIDENCE  = 2,
    ROLLBACK_HIGH_LATENCY    = 3,
    ROLLBACK_HIGH_ERROR_RATE = 4,
};

class RollbackManager {
public:
    RollbackManager(
        ModelRuntime&     model_runtime,
        AeonProtocol&     protocol,
        CheckpointManager& checkpoint
    );

    /**
     * Evaluate current runtime health and roll back if thresholds are exceeded.
     *
     * @param stats   Current RuntimeStats
     * @param score   Latest composite score
     * @param state   Pointer to mutable AeonState (for checkpoint after rollback)
     * @return        The trigger that caused a rollback, or ROLLBACK_NONE
     */
    RollbackTrigger evaluate(
        const RuntimeStats&       stats,
        const ModelScoreResult&   score,
        AeonState*                state
    );

    /** Returns true if a rollback is currently in effect. */
    bool isRolledBack() const { return _is_rolled_back; }

    /** Reset rollback state (called when a new model is activated). */
    void reset();

private:
    ModelRuntime&      _model_runtime;
    AeonProtocol&      _protocol;
    CheckpointManager& _checkpoint;
    bool               _is_rolled_back;

    void _executeRollback(RollbackTrigger trigger, AeonState* state);
    static const char* _triggerName(RollbackTrigger t);
};
