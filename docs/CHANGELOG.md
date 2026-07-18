# Changelog — ÆON Home Evolution

All notable changes to the ÆON Home project are documented in this file.

---

## [1.5.0] — 2026-07-19
### Added
- **Application Services Layer**: Introduced modular Device, Telemetry, Checkpoint, and Policy Services.
- **Communication Gateway**: Created `CommunicationGateway` to coordinate active connections, retries, and validate HMAC signatures.
- **Event Bus**: Asynchronous backend event bus.
- **Comprehensive Documentation**: Complete deployment, testing, architecture, and developer guides.

## [1.4.0] — 2026-07-18
### Added
- **Dream State Optimizer**: Background memory consolidation and policy weight optimization during idle periods.
- **On-Device Learning Engine**: Dynamic adjustments to temperature settings and policy priority weights on consecutive user corrections.
- **Extended Telemetry**: 11 new protocol messages communicating dream stages and feedback events.
- **Persistent State Layout Expansion**: Appended counters for dream runs and feedback actions to `AeonState` (struct size 70 bytes).
- **Version Bump**: Bounded `STORAGE_MAGIC` to `0xAE07`.

## [1.3.0] — 2026-07-15
### Added
- **Cognitive OS Subsystems**: Implemented NetworkX Decision Graph, alternative action rankings, and explainable reason codes.
- **Cognitive Memory**: Organized transient memories into 8 categories with automatic capacity pruning.
- **Registry Attributes**: Track device health, reliability metrics, and response times.

## [1.2.0] — 2026-07-10
### Added
- **Hot-Deployment pipeline**: Support local retraining loops, model packaging, validation checks, and latency-based rollbacks.
