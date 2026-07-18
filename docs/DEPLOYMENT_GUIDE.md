# Deployment Guide — Production Setup & Maintenance

This guide explains how to deploy, flash, monitor, and rollback the complete ÆON Home architecture in production.

---

## 1. Backend Host Deployment

For permanent setups, run the edge server node as a systemd background service on the Snapdragon host machine.

### systemd Service Configuration
1. Create `/etc/systemd/system/aeon-backend.service`:
   ```ini
   [Unit]
   Description=ÆON Home Backend Edge Host
   After=network.target

   [Service]
   Type=simple
   User=aeon
   WorkingDirectory=/home/aeon/aeon-home/backend
   ExecStart=/home/aeon/aeon-home/backend/.venv/bin/python -m aeon.main
   Restart=always
   EnvironmentFile=/home/aeon/aeon-home/.env

   [Install]
   WantedBy=multi-user.target
   ```
2. Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable aeon-backend.service
   sudo systemctl start aeon-backend.service
   ```

---

## 2. Firmware Flashing

1. Connect the Arduino Uno Q to the Snapdragon PC or target flashing device via USB.
2. Locate the port (e.g. `/dev/ttyACM0` or `COM3`).
3. Flash using `arduino-cli`:
   ```bash
   ./scripts/flash_arduino.sh /dev/ttyACM0 arduino:samd:nano_33_iot
   ```
   *(Ensure you update the board FQBN and port parameters according to your physical setup).*

---

## 3. Model Hot-Deployment Lifecycle

Updating active inference models follows a staged pipeline to prevent automation disruption:

```
[ RETRAIN ] ──► [ VALIDATE ] ──► [ COMPILE BIN ] ──► [ UPLOAD ] ──► [ COMPARE & VERIFY ] ──► [ ACTIVATE ]
                                                                                                    │
                                                                                                    ▼
                                                                                            [ ROLLBACK (on fail) ]
```

1. **Retraining**: Snapdragon retrains the linear classifier models with accumulated override datasets.
2. **Validation**: Compares accuracy, precision, and latencies against safety thresholds.
3. **Packaging**: Compiles the model using QNN Hexagon NPU compiler tools.
4. **Activation**: Instructs the edge node to hot-swap to the new model version.
5. **Rollback Trigger**: If average latencies spike or error rates exceed 5% over a 10-second window, the system automatically triggers a rollback to the stable backup version.
