# Models

All AI models used by the ÆON QNN runtime.

## Directory layout

```
models/
  src/          Source ONNX models + quantisation configs
  bin/          Compiled QNN .bin models (Hexagon HTP target)
  training/     Training scripts for each model
  README.md     This file
```

## Model catalogue

### presence_classifier
- **Task:** Binary classification — is someone home?
- **Input:** `[1, 7]` float32 feature vector
- **Output:** `[1, 2]` softmax (class 0 = absent, class 1 = present)
- **Architecture:** 3-layer MLP, ~8K parameters
- **Training data:** Labelled feature vectors from user feedback loop

### anomaly_detector
- **Task:** Anomaly scoring — how unusual is this reading?
- **Input:** `[1, 7]` float32 feature vector
- **Output:** `[1, 1]` anomaly score 0–1
- **Architecture:** Autoencoder reconstruction error
- **Training data:** Unlabelled stream (unsupervised)

### occupancy_predictor
- **Task:** Predict occupancy for next 6 time slots (30-min intervals)
- **Input:** `[1, 24, 7]` float32 — 24-step history
- **Output:** `[1, 6]` probability per slot
- **Architecture:** Lightweight LSTM, ~32K parameters
- **Training data:** Historical feature frames from memory store

## Compiling to QNN

```bash
# Requires QNN SDK on PATH
python -m aeon.models.export_to_qnn --all
```

## Fallback

If `.bin` files are absent, `QNNRuntime` falls back to the `.onnx` files
in `src/` using ONNX Runtime CPU. Performance will be lower but the system
remains functional.
