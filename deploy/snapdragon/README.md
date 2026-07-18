# ÆON Home — Snapdragon Edge AI Deployment

This guide is for deploying ÆON Home to Qualcomm Snapdragon platforms (specifically X Elite Windows on ARM [WoA] and Linux variants), leveraging the Hexagon NPU for offline, private AI inferences via the Qualcomm Neural Processing SDK (QNN).

## Deployment Strategy: Bare Metal vs. Docker

> [!IMPORTANT]
> **Recommended: Bare Metal (Direct OS)**
> For Snapdragon platforms, we strongly recommend deploying directly to the host OS using the provided Windows or Linux startup scripts, rather than Docker. 
> 
> Running Docker on Windows on ARM creates a Hyper-V virtualization layer that significantly complicates direct hardware access (passing through USB serial ports to the Arduino Sentinel, and mapping Hexagon DSP memory blocks to the container). 

## Prerequisites
1. **Qualcomm Neural Processing SDK**: Ensure you have installed the QNN SDK.
2. **ONNX Runtime (QNN EP)**: Ensure `onnxruntime` is compiled or installed with the `QNNExecutionProvider`.
3. Python 3.10+ (ARM64 native build).
4. Node.js v22+ (ARM64 native build).

## Windows (WoA) Deployment

1. Run the `setup_qnn.bat` script located in this directory to load the correct QNN environment variables.
2. Ensure your Arduino is plugged in via USB (check Device Manager for the COM port, and set it in your `.env` file).
3. From the repository root, run `deploy\windows\start_aeon.bat`.

## Linux Deployment

1. Run the `setup_qnn.sh` script to set `QNN_SDK_ROOT` and `ADSP_LIBRARY_PATH`.
2. Copy the systemd services:
   ```bash
   sudo cp deploy/systemd/*.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now aeon-backend aeon-frontend
   ```

## Metrics
When deployed, you can visit `http://localhost:9090` to view the direct hardware telemetry (simulated if QNN direct hardware polling APIs are restricted by OS boundaries).
