#ifndef AEON_ACTUATORS_H
#define AEON_ACTUATORS_H

#include <Arduino.h>

// Init actuator pins
void actuators_init();

// Set relay state
void actuators_set_relay(uint8_t relay_id, bool state);

// Set status LED state (pin 5)
void actuators_set_led(bool state);

// Play feedback beep sequence
void actuators_play_beep(uint8_t beep_type);

#endif // AEON_ACTUATORS_H
