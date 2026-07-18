#pragma once
#include <Arduino.h>
#include "../storage/runtime_state.h"
#include "../protocols/aeon_protocol.h"

class DreamState {
public:
    enum State {
        DREAM_IDLE,
        DREAM_RUNNING,
        DREAM_INTERRUPTED,
        DREAM_COMPLETED
    };

    DreamState(AeonProtocol& protocol);

    void init(AeonState* state);

    // Checks eligibility based on CPU/idle criteria
    bool checkEligibility(uint32_t last_activity_ms, bool is_deploying, bool is_queue_empty);

    // Execution controls
    void start();
    void tick(AeonState* state);
    void interrupt(const char* reason);
    void resume();
    
    State getState() const { return _state; }
    uint32_t getDreamDurationMs() const { return _dream_duration_ms; }

private:
    AeonProtocol& _protocol;
    State _state;
    uint32_t _dream_start_ms;
    uint32_t _dream_duration_ms;
    uint8_t _optimization_stage;
};
