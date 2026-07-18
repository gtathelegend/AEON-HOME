# ÆON Sentinel Model Runtime & Inference Subsystems

This document describes the on-device model runtime and associated subsystems deployed on the **Arduino UNO Q** (or Arduino UNO R4 WiFi) edge node. The edge node is solely responsible for inference, scoring, confidence estimation, and raw training sample accumulation, with zero local training.

---

## 1. Inference Engine (`ModelRuntime`)

The core inference engine executes a **Statistical Z-Score Anomaly Detector** on incoming sensor readings (primarily temperature). 

### 1.1 Anomaly Scoring Mathematical Formulation

For a raw temperature reading $x_t$:

1. **Z-Score Calculation**:
   $$\text{score}(x_t) = \frac{|x_t - \mu|}{\sigma}$$
   where $\mu$ is the rolling mean and $\sigma$ is the rolling standard deviation of the active model version.

2. **Prediction Output**:
   $$\hat{y}_t = \begin{cases} 1 & \text{if } \text{score}(x_t) > \theta \\ 0 & \text{otherwise} \end{cases}$$
   where $\theta$ is the decision threshold.

3. **Raw Confidence (Sigmoid Calibration)**:
   $$\text{conf}_{\text{raw}} = \text{sigmoid}(\text{score}(x_t) - \theta) = \frac{1}{1 + e^{-(\text{score}(x_t) - \theta)}}$$
   This calibrates the anomaly distance relative to the decision boundary into a raw probability $P(\text{anomaly} \mid x_t) \in [0, 1]$.

---

## 2. Confidence Calibration Engine (`ConfidenceEngine`)

To prevent noise and transient anomalies from triggering false alarms, the `ConfidenceEngine` applies **four adjustment factors** to the raw confidence:

$$\text{conf}_{\text{final}} = \text{clamp}\left( \text{conf}_{\text{raw}} + \Delta_{\text{stability}} + \Delta_{\text{runtime}} + \Delta_{\text{historical}} + \Delta_{\text{context}},\, 0.0,\, 1.0 \right)$$

### 2.1 Adjustment Factors

1. **Stability Adjustment ($\Delta_{\text{stability}}$)**:
   Penalizes high variance in recent model predictions to prevent fluttering.
   $$\Delta_{\text{stability}} = -\left(\min\left(1.0, \frac{\text{Var}(\text{confidence})}{\text{Var}_{\text{limit}}}\right) \times W_{\text{stability\_penalty}}\right)$$
   *Default weights: $\text{Var}_{\text{limit}} = 0.04$, $W_{\text{stability\_penalty}} = 0.20$.*

2. **Runtime Adjustment ($\Delta_{\text{runtime}}$)**:
   Penalizes confidence when the firmware encounters elevated inference failure/error rates.
   $$\Delta_{\text{runtime}} = -(\text{Error Rate} \times W_{\text{error\_penalty}})$$
   *Default weight: $W_{\text{error\_penalty}} = 0.15$.*

3. **Historical Adjustment ($\Delta_{\text{historical}}$)**:
   Compares the current raw confidence to the long-term running average confidence baseline.
   $$\Delta_{\text{historical}} = \text{clamp}\left(\frac{\text{conf}_{\text{raw}} - \text{conf}_{\text{avg\_historical}}}{0.20} \times W_{\text{historical\_adj}},\, -W_{\text{historical\_adj}},\, W_{\text{historical\_adj}}\right)$$
   *Default weight: $W_{\text{historical\_adj}} = 0.10$.*

4. **Contextual Adjustment ($\Delta_{\text{context}}$)**:
   Reserved for time-of-day/occupancy adjustments (currently behaves as $0.0$ placeholder).

---

## 3. Composite Model Scorer (`ModelScorer`)

Evaluates the overall quality of the executing model in real-time, yielding a composite score:

$$\text{Score}_{\text{composite}} = \sum (C_i \cdot W_i) \times \text{Decay}_{\text{age}}$$

### 3.1 Score Components ($C_i$) and Weights ($W_i$)

| Component ($C_i$) | Calculation | Weight ($W_i$) |
| :--- | :--- | :--- |
| **Confidence** | Running average confidence $\in [0, 1]$ | $0.25$ |
| **Accuracy** | Off-device holdout validation accuracy estimate | $0.20$ |
| **Correction** | $1 - \text{Correction Rate}$ (frequency of user overrides) | $0.15$ |
| **Latency** | Speed score: $1 - \frac{\text{avg\_latency} - \text{ref}}{\text{max} - \text{ref}}$ (lower is better) | $0.10$ |
| **Reliability** | $1 - \text{Error Rate}$ (percentage of successful inferences) | $0.15$ |
| **Rollback** | Penalty based on previous rollbacks for this version | $0.10$ |
| **Stability** | $1 - \text{Variance Normalized}$ (lower variance is better) | $0.05$ |

### 3.2 Age Decay Factor ($\text{Decay}_{\text{age}}$)
Models degrade in relevance as physical home characteristics shift (drift). A half-life decay is applied after a grace period:

$$\text{Decay}_{\text{age}} = \begin{cases} 1.0 & \text{if } t_{\text{age}} \le 7\text{ days} \\ \max\left(0.5, e^{-\ln(2) \frac{t_{\text{age}} - 7\text{ days}}{14\text{ days}}}\right) & \text{if } t_{\text{age}} > 7\text{ days} \end{cases}$$

---

## 4. Automatic Rollback Manager (`RollbackManager`)

Monitors the model score and statistics during runtime health evaluations. A rollback to the previous working model version is triggered if **any** of the following conditions are met:

1. **Composite Score Failure**: $\text{Score}_{\text{composite}} < 0.30$
2. **Confidence Collapse**: $\text{conf}_{\text{avg}} < 0.25$
3. **Latency Spike**: $\text{avg\_latency\_ms} > 500\text{ ms}$
4. **Reliability Collapse**: $\text{error\_rate} > 0.30$

---

## 5. Ring Learning Buffer (`LearningBuffer`)

To support continuous learning, the firmware records inference inputs and outputs locally in a fixed-size circular ring buffer (`LEARNING_BUFFER_CAPACITY = 128`).

- **Ring Semantics**: When full, the oldest un-flushed samples are overwritten.
- **Power Loss Protection**: Buffer write-head and count are persisted in `AeonState` flash slots.
- **Snapdragon Synchronisation**: Every 2 minutes (or upon buffer saturation), the pending batch is flushed over the WebSocket bus as `learning_record` JSON frames for training dataset accumulation.
