/**
 * actuator_driver.cpp — Actuator driver implementation.
 */
#include "actuator_driver.h"
#include "../runtime/runtime_config.h"

ActuatorDriver::ActuatorDriver() {}

void ActuatorDriver::init() {
    pinMode(PIN_LED, OUTPUT);
    digitalWrite(PIN_LED, LOW);

    pinMode(PIN_FAN_PWM, OUTPUT);
    pinMode(PIN_FAN_IN1, OUTPUT);
    pinMode(PIN_FAN_IN2, OUTPUT);
    digitalWrite(PIN_FAN_IN1, HIGH);
    digitalWrite(PIN_FAN_IN2, LOW);
    analogWrite(PIN_FAN_PWM, 0);

    pinMode(PIN_BUZZER, OUTPUT);
    digitalWrite(PIN_BUZZER, LOW);
}

void ActuatorDriver::setFanSpeed(uint8_t percent) {
    if (percent > 100) percent = 100;
    // Map 0-100% to 0-255 PWM
    uint8_t pwm = (percent * 255) / 100;
    digitalWrite(PIN_FAN_IN1, HIGH);
    digitalWrite(PIN_FAN_IN2, LOW);
    analogWrite(PIN_FAN_PWM, pwm);
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
