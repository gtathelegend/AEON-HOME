/**
 * runtime_state.h — Persistent runtime state struct for ÆON Sentinel.
 *
 * This struct is the single source of truth for everything persisted to flash.
 * Only StorageManager may read or write this to flash.
 *
 * ─── MIGRATION NOTES ────────────────────────────────────────────────────────
 *
 * FORMAT HISTORY
 *   v1 (STORAGE_MAGIC 0xAE04): Original 10 fields, 40 bytes
 *   v2 (STORAGE_MAGIC 0xAE04): Aspirational assert at 44 bytes (same format)
 *   v3 (STORAGE_MAGIC 0xAE05): Added 9 persistent runtime stats / buffer
 *       fields at end of struct (before crc32). New size = 62 bytes.
 *
 * VERSION CHECK BEHAVIOUR
 *   On boot, StorageManager reads the slot magic.
 *   If magic != STORAGE_MAGIC (0xAE05), the slot is rejected.
 *   An old v1/v2 slot (magic 0xAE04) will be rejected by the updated
 *   StorageManager and applyDefaults() will be called, ensuring the firmware
 *   never operates on partially compatible flash data.
 *
 * LAYOUT STABILITY
 *   Never insert fields in the middle of this struct.
 *   Always append new fields immediately before crc32.
 *   Always update the static_assert and bump STORAGE_MAGIC on layout change.
 *
 * DO NOT PERSIST transient values (scheduler timers, packet buffers, etc.).
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

    // ── Runtime statistics (added v3 / STORAGE_MAGIC 0xAE05) ─────────────────
    // These survive power loss to maintain continuity of model performance data.
    // Fixed-point encoding: x100 means the value is stored as (real_value * 100)
    // to avoid floating-point in flash layout.
    uint32_t inference_count;        // Total inferences since model activation
    uint16_t avg_confidence_x100;    // Average confidence * 100  (0–10000)
    uint16_t avg_latency_ms;         // Average inference latency in ms (0–65535)
    uint16_t error_count;            // Inference error count (saturates at 65535)
    uint16_t model_score_x100;       // Composite model score * 100 (0–10000)
    uint8_t  rollback_count;         // Rollbacks for this model version (0–255)
    uint8_t  _pad1;                  // Reserved — must be 0

    // ── Learning buffer metadata (added v3) ───────────────────────────────────
    // Ring buffer head and count persist across reboots so buffered data
    // is not lost on power loss. Actual record bytes live in a separate
    // flash region managed by LearningBuffer.
    uint16_t learning_buffer_head;   // Write-head index in the ring buffer
    uint16_t learning_buffer_count;  // Number of valid records in the buffer

    // ── Integrity (always last) ───────────────────────────────────────────────
    uint32_t crc32;              // CRC32 over all preceding fields (zeroed for calc)
};
#pragma pack(pop)

// ─── Size assertion ───────────────────────────────────────────────────────────
// Update this constant whenever fields are added or removed.
// The compiler will catch accidental struct expansion or shrinkage.
//
// Layout breakdown (pack 1, no padding):
//   checkpoint_id        4
//   seq                  4
//   timestamp            4
//   model_v              4
//   mean                 4
//   std_dev              4
//   theta                4
//   active_policy_hash   4
//   deployment_id        4
//   inference_count      4
//   avg_confidence_x100  2
//   avg_latency_ms       2
//   error_count          2
//   model_score_x100     2
//   rollback_count       1
//   _pad1                1
//   learning_buffer_head 2
//   learning_buffer_count 2
//   crc32                4
//                     ----
//   TOTAL               58 bytes
static_assert(sizeof(AeonState) == 58, "AeonState layout changed — update STORAGE_SLOT layout and STORAGE_MAGIC");
