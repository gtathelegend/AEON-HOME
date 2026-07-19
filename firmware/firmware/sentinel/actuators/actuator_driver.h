/**
 * actuator_driver.h — LED, buzzer and relay controller.
 */
#pragma once
#include <Arduino.h>

class ActuatorDriver {
public:
    ActuatorDriver();
    void init();
    void setFanSpeed(uint8_t percent);
    void setLed(bool state);
    void playBeep(uint8_t beep_type);
};
