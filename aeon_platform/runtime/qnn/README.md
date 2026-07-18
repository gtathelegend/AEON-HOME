# QNN — Qualcomm Neural Network Runtime

This module wraps the **Qualcomm AI Engine Direct (QNN) SDK** to run quantised
AI models on the **Hexagon NPU** inside Snapdragon X Elite.

## Model pipeline

```
Raw ONNX / PyTorch model
      ↓  (quantise + compile)
  qnn-net-run / AI Hub
      ↓
  model.bin  (HTP/Hexagon binary)
      ↓
  QNNRuntime.infer()
```

## Models

| File                          | Input shape | Output        | Notes                     |
|-------------------------------|-------------|---------------|---------------------------|
| `presence_classifier.bin`     | [1, 7]      | [1, 2]        | Is someone home?          |
| `anomaly_detector.bin`        | [1, 7]      | [1, 1] score  | Unusual pattern score     |
| `occupancy_predictor.bin`     | [1, 24, 7]  | [1, 6]        | Next 6-slot occupancy     |

Input feature vector (7 dims):
  [temperature, humidity, motion, door_open, mean_temp, var_temp, delta_motion]

## Installation

1. Download the QNN SDK from https://developer.qualcomm.com/software/qualcomm-ai-engine-direct-sdk
2. Install the Python wheel: `pip install <sdk>/python/qnn-*.whl`
3. Place compiled `.bin` files in `backend/models/bin/`

## Fallback

Without the QNN SDK, the runtime transparently falls back to ONNX Runtime CPU.
Place `.onnx` files in `backend/models/bin/` for development on non-Snapdragon hardware.
