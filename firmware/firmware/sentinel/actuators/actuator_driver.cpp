/**
 * actuator_driver.cpp — Actuator driver implementation.
 */
#include "actuator_driver.h"
#include "../runtime/runtime_config.h"

ActuatorDriver::ActuatorDriver() {}

void ActuatorDriver::init() {
    pinMode(PIN_LED, OUTPUT);
    digitalWrite(PIN_LED, LOW);

    pinMode(PIN_RELAY_1, OUTPUT);
    digitalWrite(PIN_RELAY_1, LOW);

    pinMode(PIN_RELAY_2, OUTPUT);
    digitalWrite(PIN_RELAY_2, LOW);

    pinMode(PIN_BUZZER, OUTPUT);
    digitalWrite(PIN_BUZZER, LOW);
}

void ActuatorDriver::setRelay(uint8_t relay_id, bool state) {
    uint8_t pin = (relay_id == 1) ? PIN_RELAY_1 : PIN_RELAY_2;
    digitalWrite(pin, state ? HIGH : LOW);
}

void ActuatorDriver::setLed(bool state) {
    digitalWrite(PIN_LED, state ? HIGH : LOW);
}

void ActuatorDriver::playBeep(uint8_t beep_type) {
    // beep_type = 1: one short beep
    // beep_type = 2: two short beeps
    if (beep_type == 1) {
        tone(PIN_BUZZER, 1000, 50);
    } else if (beep_type == 2) {
        tone(PIN_BUZZER, 1000, 50);
        delay(100);
        tone(PIN_BUZZER, 1000, 50);
    }
}
