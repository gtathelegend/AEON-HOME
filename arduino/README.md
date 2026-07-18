# Arduino — ÆON Sentinel Firmware

The Arduino layer is the **sensing and actuation edge** of ÆON Home.  
It handles raw hardware, performs lightweight feature extraction, and communicates
with the Snapdragon AI PC over USB serial using the AEON binary protocol.

## Directory layout

```
arduino/
  firmware/
    sentinel/         Main sketch — reads sensors, checkpoints, talks to Snapdragon
  libraries/
    aeon_protocol/    Binary serial framing (magic + CRC-16)
    aeon_checkpoint/  EEPROM ping-pong state persistence
    aeon_sensors/     DHT22 + PIR + reed-switch abstraction
    aeon_features/    Rolling-window feature extraction
```

## Hardware

| Component          | Default pin | Notes                              |
|--------------------|-------------|------------------------------------|
| DHT11              | 2           | Temp + humidity                    |
| HC-SR501 PIR       | 3           | Motion detection                   |
| False Alarm Button | 4           | Manual dismissal / threshold bump |
| Status LED         | 5           | Active anomaly / alert indicator   |

## Supported boards

- Arduino Uno R4 WiFi (recommended)
- Arduino Nano 33 IoT
- Any AVR/ARM board with ≥ 1 KB EEPROM and hardware serial

## Setup

1. Install Arduino IDE 2.x or arduino-cli.
2. Install libraries: `ArduinoJson`, `DHT sensor library`.
3. Copy `libraries/aeon_*` folders into your Arduino `libraries/` directory.
4. Open `firmware/sentinel/sentinel.ino` and flash.

## Serial protocol

See `libraries/aeon_protocol/aeon_protocol.h` for the full frame spec.  
The Snapdragon backend serial bridge connects on the same USB-serial port at **115200 baud**.

## EEPROM layout

Two 64-byte ping-pong slots starting at address 0.  
Each slot: `[MAGIC:4][VERSION:1][STATE:sizeof(AeonState)][CRC16:2]`  
Recovery latency target: **< 200 ms** from power-on.
