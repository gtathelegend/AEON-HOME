/**
 * runtime_state.h — Persistent runtime state struct for ÆON Sentinel.
 *
 * This struct is the single source of truth for everything persisted to flash.
 * Only StorageManager may read or write this to flash.
 *
 * Layout is stable — changing field order will invalidate existing checkpoints.
 */
#pragma once
#include <stdint.h>

#pragma pack(push, 1)
struct AeonState {
    // ── Checkpoint identity ──────────────────────────────────────────────────
    uint32_t checkpoint_id;      // Monotonically increasing checkpoint counter
    uint32_t seq;                // Global frame sequence counter
    uint32_t timestamp;          // millis() at last checkpoint

    // ── Model parameters (updated by model_update command) ───────────────────
    uint32_t model_v;            // Active model version
    float    mean;               // Rolling temperature mean (from trainer)
    float    std_dev;            // Rolling temperature std dev (from trainer)
    float    theta;              // Anomaly detection threshold (°C)

    // ── Policy state ─────────────────────────────────────────────────────────
    uint32_t active_policy_hash; // Hash of the currently active policy set

    // ── Deployment metadata ───────────────────────────────────────────────────
    uint32_t deployment_id;      // ID of last applied deployment (0 = none)

    // ── Integrity ─────────────────────────────────────────────────────────────
    uint32_t crc32;              // CRC32 over all preceding fields (zeroed for calc)
};
#pragma pack(pop)

// Size assertion — helps catch accidental struct expansion
static_assert(sizeof(AeonState) == 44, "AeonState layout changed — update STORAGE_SLOT layout");
