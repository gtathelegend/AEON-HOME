#include "learning_engine.h"

LearningEngine::LearningEngine(AeonProtocol& protocol)
    : _protocol(protocol),
      _policy_weight(1.0f),
      _preference_weight(1.0f),
      _activity_weight(1.0f),
      _consecutive_corrections(0)
{
}

void LearningEngine::init(AeonState* state) {
    (void)state;
    _policy_weight = 1.0f;
    _preference_weight = 1.0f;
    _activity_weight = 1.0f;
    _consecutive_corrections = 0;
}

void LearningEngine::processFeedback(const FeedbackEvent& event, AeonState* state) {
    if (!state) return;

    // Send acknowledgement
    const char* type_str = "unknown";
    if (event.type == FEEDBACK_CORRECTION) type_str = "correction";
    else if (event.type == FEEDBACK_NEGATIVE) type_str = "negative";
    else if (event.type == FEEDBACK_POSITIVE) type_str = "positive";
    else if (event.type == FEEDBACK_PREFERENCE_CHANGE) type_str = "preference_change";
    else if (event.type == FEEDBACK_POLICY_CONFLICT) type_str = "policy_conflict";

    _protocol.sendFeedbackReceived(type_str, event.target, event.value);

    // Apply feedback-driven updates
    if (event.type == FEEDBACK_CORRECTION || event.type == FEEDBACK_NEGATIVE) {
        _consecutive_corrections++;
        
        // Lower policy and model confidence as a penalty
        if (state->avg_confidence_x100 > 1000) {
            state->avg_confidence_x100 -= 500; // Decrement confidence by 5%
        }
        
        // If consecutive overrides occur, adapt preferred temperature setting
        if (_consecutive_corrections >= 3 && strcmp(event.target, "temp") == 0) {
            state->preferred_temp = event.value;
            _protocol.sendPreferenceUpdated("preferred_temp", state->preferred_temp);
            _consecutive_corrections = 0;
        }

        // Slowly adapt policy weight downwards on manual overrides
        if (_policy_weight > 0.2f) {
            _policy_weight -= 0.1f;
            _protocol.sendPolicyAdapted("local_policy", _policy_weight);
        }
    } else if (event.type == FEEDBACK_POSITIVE) {
        _consecutive_corrections = 0;
        // Rebuild policy weight on success
        if (_policy_weight < 1.0f) {
            _policy_weight += 0.05f;
            _protocol.sendPolicyAdapted("local_policy", _policy_weight);
        }
    } else if (event.type == FEEDBACK_PREFERENCE_CHANGE) {
        state->preferred_temp = event.value;
        _protocol.sendPreferenceUpdated("preferred_temp", state->preferred_temp);
        _consecutive_corrections = 0;
    }
}

void LearningEngine::evaluateDecision(const char* action, float confidence, bool success, AeonState* state) {
    if (!state) return;

    state->inference_count++;
    
    // EMA update for average confidence: new_avg = 0.95 * old_avg + 0.05 * new_conf
    uint16_t conf_x100 = static_cast<uint16_t>(confidence * 10000.0f);
    state->avg_confidence_x100 = static_cast<uint16_t>(
        0.95f * state->avg_confidence_x100 + 0.05f * conf_x100
    );

    // Increment error count on execution/success failure
    if (!success && state->error_count < 65535) {
        state->error_count++;
    }

    // Trigger local policy weight restoration on success
    if (success && _policy_weight < 1.0f) {
        _policy_weight = min(1.0f, _policy_weight + 0.01f);
    }
}
