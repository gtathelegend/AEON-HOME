# ÆON Home Hardware Setup

## Required Hardware
- 1x Arduino Uno (or compatible)
- 1x ESP8266 NodeMCU (or compatible)
- 1x DHT11 Temperature/Humidity Sensor
- 1x PIR Motion Sensor
- 1x Push Button (False Alarm feedback)
- 1x LED (Anomaly Indicator)
- 1x I2C AT24C256 EEPROM Module (optional, uses internal EEPROM fallback)
- Resistors: 3x 220Ω (for logic level shifting and LED)
- Jumper wires and Breadboard

## Wiring Diagram

### Arduino -> Sensors & Actuators
- **DHT11 Data** -> Arduino D2
- **PIR Motion Data** -> Arduino D3
- **Button (Active LOW)** -> Arduino D4 (internal pullup)
- **LED (Active HIGH)** -> Arduino D5 (via 220Ω resistor)
- **EEPROM** -> I2C (SDA = A4, SCL = A5)

### Arduino -> ESP8266 (UART Bridge)
Since the ESP8266 operates at 3.3V and the Arduino at 5V, a voltage divider is required for the Arduino's TX line.

1. **Arduino D10 (RX)** -> ESP8266 D6 / GPIO12 (TX) (Direct connection, ESP8266 3.3V TX is read safely by Arduino 5V RX)
2. **Arduino D11 (TX)** -> ESP8266 D5 / GPIO14 (RX) **(VIA VOLTAGE DIVIDER)**
   - Arduino D11 -> 220Ω -> Node -> ESP8266 D5
   - Node -> 220Ω -> 220Ω -> GND
3. **Common Ground**: Connect Arduino GND to ESP8266 GND.

## Power
- Power the Arduino via USB or 9V barrel jack.
- Power the ESP8266 via its own USB port, or a regulated 3.3V/5V supply to its Vin pin. Do not pull heavy current from the Arduino's 3.3V pin.
