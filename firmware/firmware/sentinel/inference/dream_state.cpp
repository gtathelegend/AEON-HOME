#include "dream_state.h"

DreamState::DreamState(AeonProtocol& protocol)
    : _protocol(protocol),
      _state(DREAM_IDLE),
      _dream_start_ms(0),
      _dream_duration_ms(0),
      _optimization_stage(0)
{
}

void DreamState::init(AeonState* state) {
    (void)state;
    _state = DREAM_IDLE;
    _dream_start_ms = 0;
    _dream_duration_ms = 0;
    _optimization_stage = 0;
}

bool DreamState::checkEligibility(uint32_t last_activity_ms, bool is_deploying, bool is_queue_empty) {
    if (_state == DREAM_RUNNING) return false;
    if (is_deploying) return false;
    if (!is_queue_empty) return false;

    // Check if idle for more than 10 seconds
    uint32_t idle_time = millis() - last_activity_ms;
    return (idle_time > 10000);
}

void DreamState::start() {
    _state = DREAM_RUNNING;
    _dream_start_ms = millis();
    _optimization_stage = 1;
    _protocol.sendDreamStarted();
    Serial.println("[Dream] Entering Dream State optimization loop...");
}

void DreamState::tick(AeonState* state) {
    if (_state != DREAM_RUNNING) return;

    // Simulate multi-stage optimization ticks
    if (_optimization_stage == 1) {
        // Stage 1: Memory Consolidation & Pruning
        Serial.println("[Dream] Stage 1: Memory consolidation running...");
        _optimization_stage = 2;
    } 
    else if (_optimization_stage == 2) {
        // Stage 2: Policy & Activity Weight Tuning
        Serial.println("[Dream] Stage 2: Tuning policy and activity confidence...");
        
        // Slowly improve overall confidence on dream optimization if no errors
        if (state && state->error_count == 0 && state->avg_confidence_x100 < 9500) {
            state->avg_confidence_x100 += 50;  // 0.5% boost
        }

        _optimization_stage = 3;
    }
    else if (_optimization_stage == 3) {
        // Stage 3: Completion and Report transmission
        _dream_duration_ms = millis() - _dream_start_ms;
        _state = DREAM_COMPLETED;

        if (state) {
            state->dream_run_count++;
        }

        Serial.print("[Dream] Optimization complete. Duration: ");
        Serial.print(_dream_duration_ms);
        Serial.println(" ms");

        _protocol.sendDreamCompleted(_dream_duration_ms, 5);  // Consolidated 5 memories
    }
}

void DreamState::interrupt(const char* reason) {
    if (_state != DREAM_RUNNING) return;

    _dream_duration_ms = millis() - _dream_start_ms;
    _state = DREAM_INTERRUPTED;
    _protocol.sendDreamInterrupted(reason);

    Serial.print("[Dream] Interrupted! Reason: ");
    Serial.print(reason);
    Serial.print(", Duration: ");
    Serial.print(_dream_duration_ms);
    Serial.println(" ms");
}

void DreamState::resume() {
    if (_state != DREAM_INTERRUPTED) return;
    _state = DREAM_RUNNING;
    _dream_start_ms = millis();
    Serial.println("[Dream] Resuming Dream State optimization...");
}
