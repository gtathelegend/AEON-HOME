/**
 * actuator_driver.h — LED, buzzer and relay controller.
 */
#pragma once
#include <Arduino.h>

class ActuatorDriver {
public:
    ActuatorDriver();
    void init();
    void setRelay(uint8_t relay_id, bool state);
    void setLed(bool state);
    void playBeep(uint8_t beep_type);
};
