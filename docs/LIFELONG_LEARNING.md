# Lifelong Learning Documentation

Lifelong learning in ÆON divides tasks between edge execution (Arduino UNO Q) and central model optimization (Snapdragon PC).

---

## 1. Division of Learning Responsibilities

Learning responsibilities are strictly separated to respect edge resource limits:

| Task Concern | Snapdragon PC (Backend) | Arduino UNO Q (Firmware) |
| :--- | :---: | :---: |
| **Neural Network Training** | ✅ Yes | ❌ No |
| **Dataset Assembly** | ✅ Yes | ❌ No |
| **Model Verification** | ✅ Yes | ❌ No |
| **Feedback Processing** | ❌ No | ✅ Yes |
| **Preference Adaptation** | ❌ No | ✅ Yes |
| **Dream Optimization** | ❌ No | ✅ Yes |
| **Memory Consolidation** | ❌ No | ✅ Yes |

---

## 2. Continuous Learning Dataset Generation

The Arduino collects telemetry and logs feature frames into a persistent learning ring buffer:
- **Frame contents**: Context snapshots, inferred activities, execution outcomes, manual override flags, and confidence scores.
- **Dataset compilation**: During statistics flush intervals, the buffered records are transmitted to the Snapdragon PC.
- **Model Retraining**: The Snapdragon PC incorporates the compiled override logs into its dataset pipelines, retrains the linear classifier models, validates metrics, and packages the updated binary for future hot-deployments back to the edge node.
