/**
 * ÆON Sentinel — Arduino Firmware (Redesigned)
 *
 * Implements a coordinator-based runtime architecture for the
 * Arduino UNO Q (STM32U585 MCU) persistent edge intelligence node.
 */

#include <Arduino.h>
#include "runtime/runtime_manager.h"

static RuntimeManager g_runtime;

void setup() {
    // Start debug logger console
    Serial.begin(BAUD_DEBUG);
    while (!Serial && millis() < 3000) {}

    // Initialize all subsystems via the coordinator boot pipeline
    if (!g_runtime.boot()) {
        Serial.println("[CRITICAL] Deterministic boot pipeline failed! System halted.");
        while (true) {
            // Halt
        }
    }
}

void loop() {
    // Delegate execution to RuntimeManager coordinator
    g_runtime.tick();
}
