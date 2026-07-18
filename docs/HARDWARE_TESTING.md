# Hardware Testing Procedure

After assembling the hardware according to `HARDWARE_SETUP.md` and flashing the firmware to both the Arduino and ESP8266, follow these 9 stages to verify the pipeline.

## Stage 1: Arduino -> ESP UART Test
1. Connect the ESP8266 to your PC via USB.
2. Open the Arduino IDE Serial Monitor (115200 baud).
3. Verify you see `[AEON-GATEWAY] Booting...`.
4. The ESP8266 should print `[UART] Received valid JSON: {"typ":"sensor_update",...}` roughly every 500ms as the Arduino sends data.

## Stage 2: Wi-Fi Connection Test
1. Turn on the Windows Mobile Hotspot on your Snapdragon PC. (Ensure SSID matches `config.h`).
2. Watch the ESP8266 Serial Monitor.
3. Verify it prints `[WIFI] Connected! IP: 192.168.137.x`.

## Stage 3: WebSocket Connection Test
1. Start your Snapdragon Python WebSocket backend.
2. Watch the ESP8266 Serial Monitor.
3. Verify it prints `[WS] Connected to url: /ws/device`.
4. Verify the backend logs indicate `gateway_register` was received.

## Stage 4: Sensor Telemetry Test
1. Observe the PC backend logs or dashboard.
2. Verify that `sensor_update` JSON events are arriving continuously.
3. Breathe on the DHT11 sensor to increase humidity/temperature and verify the changes reflect on the dashboard.

## Stage 5: Offline Buffering Test
1. Stop the Python WebSocket backend script.
2. Observe the ESP8266 Serial Monitor; it should say `[WS] Disconnected!`.
3. The ESP8266 should start buffering the most recent 10 messages (older ones are dropped).
4. Restart the Python backend.
5. Watch the ESP8266 Serial Monitor; it should print `[QUEUE] Flushing message:` and send the buffered messages.

## Stage 6: Command Gateway Test (Snapdragon -> ESP -> Arduino)
1. Use your backend to issue a manual `policy_update` command (e.g. set `theta` to 28.0).
2. The ESP8266 should print `[WS] Received: ...` and forward it.
3. The Arduino should beep 1 time, indicating it applied the policy.
4. The Arduino will send a `policy_ack` back up to the dashboard.

## Stage 7: Model Deployment Test
1. Use the Snapdragon PC to simulate a new AI model deployment (e.g., `model_v: 2`).
2. The Arduino will beep 2 times, indicating it applied a `model_update`.
3. Check the dashboard to verify a `model_ack` was received with `status: applied` and `model_v: 2`.
4. Wait 5 seconds; subsequent `heartbeat` messages should now contain `model_v: 2`.

## Stage 8: Power Persistence Test (EEPROM)
1. Ensure the Arduino is currently on `model_v: 2` (from Stage 7).
2. Unplug power to the Arduino completely.
3. Plug power back in.
4. Watch the backend logs. You should receive a `memory_status` event containing `status: restored` and `model_v: 2`.
5. If EEPROM failed, it will send `defaults_loaded` and `model_v: 1`.

## Stage 9: Dashboard Real-Time Test
1. Open the Phone PWA (connected to the same Wi-Fi) and the PC Dashboard.
2. Trigger the PIR Motion sensor.
3. The LED on the Arduino should illuminate immediately.
4. Within ~100ms, the motion indicator should turn active on BOTH the Phone and PC dashboards simultaneously without requiring a page refresh.
