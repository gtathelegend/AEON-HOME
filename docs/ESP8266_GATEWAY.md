# ESP8266 Wi-Fi Gateway

The ESP8266 acts purely as a transport bridge between the local Arduino sensor node and the powerful Snapdragon Edge AI Engine backend.

## Why a Gateway?

The Arduino Uno performs hardware sensing and hard-realtime actuation, but it lacks Wi-Fi. 
The Snapdragon X Elite performs complex AI inference and policy generation, but it lacks GPIO pins for sensors.
The ESP8266 bridges this gap by relaying UART (serial) commands over Wi-Fi via WebSockets.

## Capabilities

1. **Transparent Bridging:** Converts `SoftwareSerial` JSON messages to WebSocket JSON messages, and vice versa.
2. **Offline Buffering:** If the Snapdragon PC backend drops offline (e.g. PC restart), the ESP8266 buffers up to 10 critical events in memory and flushes them when the connection is restored.
3. **Auto-Reconnect:** Will automatically reconnect to the Mobile Hotspot and the WebSocket server if the connection drops.
4. **Gateway Telemetry:** Sends periodic `gateway_status` events so the dashboard can display Wi-Fi strength and UART health.

## Installation

1. Copy `config.example.h` to `config.h`.
2. Edit `config.h` and provide your Snapdragon PC's Mobile Hotspot SSID, Password, and IP address.
3. Flash the `aeon_wireless_gateway.ino` to your ESP8266 using the Arduino IDE.

**Required Libraries:**
- `WebSockets` by Markus Sattler (install via Arduino Library Manager)
- `ArduinoJson` by Benoit Blanchon
