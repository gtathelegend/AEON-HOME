#include "aeon_sensors.h"
#include <DHT.h>

// Hardware Pins (Pin assignment matched with older code)
#define PIN_DHT     2   // DHT11 sensor data pin
#define PIN_PIR     3   // HC-SR501 PIR motion sensor pin
#define PIN_BUTTON  4   // False alarm / dismissal button pin
#define DHT_TYPE    DHT11

static DHT dht(PIN_DHT, DHT_TYPE);

void sensors_init() {
    dht.begin();
    pinMode(PIN_PIR, INPUT);
    pinMode(PIN_BUTTON, INPUT_PULLUP);
}

void sensors_read(SensorReading* reading) {
    if (!reading) return;
    
    // Read actual DHT11 values
    reading->temperature = dht.readTemperature();
    reading->humidity    = dht.readHumidity();
    
    // Read digital states
    reading->motion    = (digitalRead(PIN_PIR) == HIGH);
    reading->door_open = (digitalRead(PIN_BUTTON) == LOW); // LOW when button pressed

    // Fallback if read error
    if (isnan(reading->temperature)) reading->temperature = -999.0f;
    if (isnan(reading->humidity))    reading->humidity    = -999.0f;
    reading->power_draw  = 12.5f; 
}

