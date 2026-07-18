# Project Roadmap — Current & Future Horizons

This document lists completed cognitive edge milestones and outlines planned future research and features.

---

## 1. Implemented Milestones (Completed)

- **Qualcomm Snapdragon X Elite Host**: FastAPI web engine, Prometheus metrics, and QNN NPU runtime fallback execution.
- **Cognitive OS Subsystems**: NETWORKX decision graphs, Alternative Action ranking, Explainability summaries, and 8-tier Cognitive Memory.
- **On-Device Learning Engine**: Dynamic correction-driven temperature preference shifting and policy weight adaptors.
- **Dream State Maintenance**: Scheduled background optimization, memory consolidation, and user action interruptions.
- **Unified Services & Gateway**: Decoupled Event Bus, and unified Communication Gateway with HMAC verification.

---

## 2. Near-Term Roadmap (Future Work)

### Matter Protocol Integration
- Integrate the Matter application layer to enable local, multi-vendor device discovery and control without relying on proprietary cloud hubs.

### Bluetooth Low Energy (BLE) Commissioning
- Implement secure BLE local provisioning from mobile devices directly to the Arduino Uno Q.

### Optimized OTA Firmware Updates
- Support encrypted over-the-air (OTA) dual-slot firmware partitions with rollback capabilities on verification failure.

### Hexagon NPU Optimizations
- Retrain context intelligence models directly in PyTorch and export using specialized Hexagon SDK Quantization pipelines.
