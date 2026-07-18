#include "aeon_policy.h"
#include "aeon_actuators.h"
#include "aeon_checkpoint.h"
#include "aeon_protocol.h"
#include <ArduinoJson.h>

static uint32_t s_active_policy_hash = 0;
static bool     s_temp_suppressed   = false;
static bool     s_motion_suppressed = false;
static float    s_temp_threshold   = 35.0f; // °C anomaly threshold

void policy_update(const char* json_str, AeonState* state) {
    if (!json_str || !state) return;
    
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, json_str);
    if (error) return;
    
    const char* typ = doc["typ"];
    if (!typ) return;
    
    if (strcmp(typ, "policy_update") == 0) {
        if (doc.containsKey("theta")) {
            s_temp_threshold = doc["theta"];
            state->theta = s_temp_threshold;
        }
        
        // Send ACK
        const char* cmd_id = doc["command_id"] | "unknown";
        StaticJsonDocument<128> ack;
        ack["typ"] = "policy_ack";
        ack["command_id"] = cmd_id;
        
        char buf[128];
        serializeJson(ack, buf);
        protocol_send_raw(buf);
        
        actuators_play_beep(1);
        checkpoint_save(state);
        
    } else if (strcmp(typ, "model_update") == 0) {
        if (doc.containsKey("model_v")) state->model_v = doc["model_v"];
        if (doc.containsKey("mean")) state->mean = doc["mean"];
        if (doc.containsKey("std")) state->std_dev = doc["std"];
        if (doc.containsKey("theta")) {
            state->theta = doc["theta"];
            s_temp_threshold = state->theta;
        }
        
        // Send ACK
        const char* cmd_id = doc["command_id"] | "unknown";
        StaticJsonDocument<128> ack;
        ack["typ"] = "model_ack";
        ack["command_id"] = cmd_id;
        ack["model_v"] = state->model_v;
        ack["status"] = "applied";
        
        char buf[128];
        serializeJson(ack, buf);
        protocol_send_raw(buf);
        
        actuators_play_beep(2);
        checkpoint_save(state);
        
    } else if (strcmp(typ, "relay_set") == 0) {
        // We only have one relay (LED) for now, but handle it generic
        bool relay_state = doc["state"];
        actuators_set_led(relay_state);
        
    } else if (strcmp(typ, "buzzer") == 0) {
        int duration = doc["duration"] | 200;
        actuators_play_beep(1); // our buzzer abstraction is simple beeps
        
    } else if (strcmp(typ, "checkpoint") == 0) {
        checkpoint_save(state);
    }
}

void policy_evaluate(const SensorReading* reading) {
    if (!reading) return;

    // False Alarm button pressed (Pin 4 active LOW)
    if (reading->door_open) {
        actuators_set_led(false);
        if (reading->motion) {
            s_motion_suppressed = true;
        }
        if (reading->temperature > s_temp_threshold) {
            s_temp_suppressed = true;
        }
        protocol_send_raw("{\"typ\":\"feedback_event\",\"device_id\":\"sentinel-01\",\"event\":\"false_alarm\"}");
        actuators_play_beep(1);
        return;
    }

    // Reset motion suppression when motion turns LOW (clear)
    if (s_motion_suppressed && !reading->motion) {
        s_motion_suppressed = false;
    }

    // Reset temperature suppression when temperature drops below threshold
    if (s_temp_suppressed && (reading->temperature <= s_temp_threshold)) {
        s_temp_suppressed = false;
    }

    bool temp_anomaly  = (!s_temp_suppressed) && (reading->temperature > s_temp_threshold);
    bool motion_active = (!s_motion_suppressed) && reading->motion;

    // LED turns ON when motion is detected or temp anomaly occurs; OFF otherwise
    actuators_set_led(temp_anomaly || motion_active);
}
