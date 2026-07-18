# ÆON Sentinel Edge Runtime Firmware

The firmware layer implements a **layered, coordinator-driven runtime** for the edge sensing and actuation node of ÆON Home.

## Target Hardware Platform
- **Board**: Arduino UNO Q (Qualcomm Dragonwing QRB2210 dual-processor system)
- **MCU**: STMicroelectronics STM32U585 (Cortex-M33 @ 160 MHz) running Arduino APIs on top of Zephyr RTOS
- **Wireless**: Built-in WCBN3536A module (Dual-band Wi-Fi 5 + Bluetooth 5.1)
- **Storage**: Emulated Non-Volatile Flash Storage (`FlashStorage_STM32`)

---

## Redesigned Modular Layout

```
firmware/firmware/sentinel/
├── sentinel.ino              ← Main sketch entry (delegates to RuntimeManager)
├── config.h                  ← Wi-Fi SSID, Password & Snapdragon WebSocket IP configurations
├── runtime/
│   ├── runtime_manager.h/.cpp   ← 13-stage deterministic boot coordinator
│   └── runtime_config.h         ← Pin assignments, intervals, and threshold constants
├── communication/
│   ├── transport.h              ← ITransport pure virtual interface
│   ├── wifi_transport.h/.cpp    ← WCBN3536A Native WebSocket client implementation
│   └── message_queue.h/.cpp     ← Reliability queue (offline ring buffer)
├── protocols/
│   ├── message_envelope.h       ← Packet metadata envelope
│   ├── aeon_protocol.h/.cpp     ← JSON frame serializer/deserializer
│   └── command_router.h/.cpp    ← Subsystem command dispatcher
├── storage/
│   ├── storage_manager.h/.cpp   ← Flash EEPROM emulation (wear-leveling, dual-slot ping-pong)
│   └── runtime_state.h          ← AeonState struct declaration
├── checkpoint/
│   └── checkpoint_manager.h/.cpp ← High-level checkpoint API
├── scheduler/
│   └── scheduler.h/.cpp         ← Cooperative task scheduler
├── telemetry/
│   └── telemetry_manager.h/.cpp ← Sensor aggregator and broadcaster
├── inference/
│   ├── model_runtime.h/.cpp     ← Model version controller
│   └── local_policy.h/.cpp      ← Local fallback rules (anomaly classifying, button feedback)
├── devices/
│   └── device_registry.h/.cpp  ← Registry for gateway and leaf devices
├── security/
│   └── security_manager.h/.cpp ← Cryptographic validation stubs
├── sensors/
│   └── sensor_driver.h/.cpp    ← DHT11 and PIR GPIO driver
├── features/
│   └── feature_extractor.h/.cpp ← Statistical feature extraction
├── actuators/
│   └── actuator_driver.h/.cpp  ← LED, relay, and buzzer driver
└── health/
    └── health_monitor.h/.cpp   ← Memory, Wi-Fi, and transport health monitoring
```

---

## Pin Configurations

| Component          | Default pin | Notes                              |
|--------------------|-------------|------------------------------------|
| DHT11              | 2           | Temp + humidity sensor             |
| HC-SR501 PIR       | 3           | Motion sensor                      |
| False Alarm Button | 4           | Manual dismissal / threshold bump  |
| Status LED         | 5           | Active anomaly / alert indicator   |
| Relay 1            | 7           | Power / appliance control          |
| Relay 2            | 8           | Auxiliary relay                    |
| Buzzer             | 9           | Acoustic indicator via tone()      |

---

## Dependency Checklist

Before compiling, install these libraries via the Arduino IDE Library Manager:
1. `ArduinoJson` (v6.x)
2. `DHT sensor library`
3. `FlashStorage_STM32`
4. `WebSockets` (by Markus Sattler)
