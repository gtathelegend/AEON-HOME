#pragma once
#include <Arduino.h>
#include "../storage/runtime_state.h"
#include "../protocols/aeon_protocol.h"

enum FeedbackType {
    FEEDBACK_POSITIVE,
    FEEDBACK_NEGATIVE,
    FEEDBACK_CORRECTION,
    FEEDBACK_PREFERENCE_CHANGE,
    FEEDBACK_POLICY_CONFLICT,
    FEEDBACK_DEVICE_FAILURE,
    FEEDBACK_FALSE_POSITIVE,
    FEEDBACK_FALSE_NEGATIVE,
    FEEDBACK_TIMEOUT,
    FEEDBACK_UNKNOWN
};

struct FeedbackEvent {
    FeedbackType type;
    uint32_t timestamp;
    float value;
    char source[16];
    char target[16];
};

class LearningEngine {
public:
    LearningEngine(AeonProtocol& protocol);

    void init(AeonState* state);
    
    // Process incoming feedback
    void processFeedback(const FeedbackEvent& event, AeonState* state);
    
    // Evaluate a finished decision
    void evaluateDecision(const char* action, float confidence, bool success, AeonState* state);

    // Getters for adaptation weights
    float getPolicyWeight() const { return _policy_weight; }
    float getPreferenceWeight() const { return _preference_weight; }
    float getActivityWeight() const { return _activity_weight; }

private:
    AeonProtocol& _protocol;
    float _policy_weight;
    float _preference_weight;
    float _activity_weight;
    uint32_t _consecutive_corrections;
};
