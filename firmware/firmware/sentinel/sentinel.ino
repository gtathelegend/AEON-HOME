/**
 * ÆON Sentinel — Arduino Firmware (Rewritten)
 *
 * This firmare provides sensing, statistical feature extraction, 
 * robust EEPROM persistence, compressed C-struct serial protocol, 
 * and actuation for the Snapdragon Edge AI Engine.
 */

#include <Arduino.h>
#include "aeon_protocol.h"
#include "aeon_checkpoint.h"
#include "aeon_sensors.h"
#include "aeon_features.h"
#include "aeon_actuators.h"
#include "aeon_policy.h"

// ── Configuration ────────────────────────────────────────────────────────────
static const uint32_t CHECKPOINT_INTERVAL_MS = 2000;
static const uint32_t SENSOR_SAMPLE_MS       = 500;
static const uint32_t SERIAL_BAUD            = 115200;

// ── State ─────────────────────────────────────────────────────────────────────
static AeonState      g_state;
static SensorReading  g_reading;
static FeatureFrame   g_frame;
static uint32_t       g_last_checkpoint = 0;
static uint32_t       g_last_sample     = 0;

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
    protocol_init(SERIAL_BAUD, 9600);
    
    // Wait for USB serial connection if applicable (e.g. Leonardo/Nano 33)
    // while (!Serial && millis() < 3000) {} 

    sensors_init();
    features_init();
    actuators_init();
    checkpoint_init();

    // Recover state from power loss
    if (checkpoint_restore(&g_state)) {
        char buf[128];
        snprintf(buf, sizeof(buf), "{\"typ\":\"memory_status\",\"device_id\":\"sentinel-01\",\"status\":\"restored\",\"model_v\":%lu,\"checksum_valid\":true}", g_state.model_v);
        protocol_send_raw(buf);
    } else {
        checkpoint_reset(&g_state);
        char buf[128];
        snprintf(buf, sizeof(buf), "{\"typ\":\"memory_status\",\"device_id\":\"sentinel-01\",\"status\":\"defaults_loaded\",\"model_v\":%lu,\"checksum_valid\":false}", g_state.model_v);
        protocol_send_raw(buf);
    }
}

// ── Loop ──────────────────────────────────────────────────────────────────────
void loop() {
    uint32_t now = millis();

    // 1. Sample sensors & extract features
    if (now - g_last_sample >= SENSOR_SAMPLE_MS) {
        g_last_sample = now;
        
        sensors_read(&g_reading);
        features_update(&g_frame, &g_reading);

        // Send sensor update over JSON serial
        protocol_send_sensor_update(&g_reading, g_state.seq++, g_state.model_v);
        
        // Send periodic heartbeat every 5 seconds
        if (g_state.seq % 10 == 0) {
            protocol_send_heartbeat(g_state.seq, g_state.model_v);
        }
        
        // Evaluate local fallback policies
        policy_evaluate(&g_reading);
    }

    // 2. Checkpoint state to EEPROM (Power-loss resilience)
    if (now - g_last_checkpoint >= CHECKPOINT_INTERVAL_MS) {
        g_last_checkpoint = now;
        g_state.timestamp = now;
        checkpoint_save(&g_state);
    }

    // 3. Process inbound compressed commands from Snapdragon
    protocol_update();
}

// ── Command handler (called by protocol layer) ────────────────────────────────
extern "C" void aeon_on_command(const char* json_str) {
    if (!json_str) return;
    
    // Dispatch to policy handler for parsing
    policy_update(json_str, &g_state);
}
