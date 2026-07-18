#include "aeon_actuators.h"

#define PIN_LED     5
#define PIN_RELAY_1 7
#define PIN_RELAY_2 8
#define PIN_BUZZER  9

void actuators_init() {
    pinMode(PIN_LED, OUTPUT);
    digitalWrite(PIN_LED, LOW);

    pinMode(PIN_RELAY_1, OUTPUT);
    digitalWrite(PIN_RELAY_1, LOW);
    
    pinMode(PIN_RELAY_2, OUTPUT);
    digitalWrite(PIN_RELAY_2, LOW);
    
    pinMode(PIN_BUZZER, OUTPUT);
    digitalWrite(PIN_BUZZER, LOW);
}

void actuators_set_relay(uint8_t relay_id, bool state) {
    uint8_t pin = (relay_id == 1) ? PIN_RELAY_1 : PIN_RELAY_2;
    digitalWrite(pin, state ? HIGH : LOW);
}

void actuators_set_led(bool state) {
    digitalWrite(PIN_LED, state ? HIGH : LOW);
}

void actuators_play_beep(uint8_t beep_type) {
    // Non-blocking buzzer would require state machine in loop(),
    // but for simple feedback a tiny blocking beep is okay (e.g. 50ms).
    // In production, use tone() asynchronously.
    tone(PIN_BUZZER, 1000, 50); // 1kHz for 50ms
}
