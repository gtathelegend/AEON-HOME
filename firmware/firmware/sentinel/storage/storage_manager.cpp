/**
 * storage_manager.cpp — Flash EEPROM persistence implementation.
 *
 * Uses FlashStorage_STM32 for Arduino UNO Q (STM32U585).
 * Dual-slot ping-pong strategy prevents corruption during power loss.
 *
 * Slot layout in emulated EEPROM address space:
 *   Offset 0                          : uint16_t magic_a
 *   Offset 2                          : AeonState slot_a
 *   Offset 2 + sizeof(AeonState)      : uint16_t magic_b
 *   Offset 4 + sizeof(AeonState)      : AeonState slot_b
 */
#include "storage_manager.h"
#include "../runtime/runtime_config.h"
#include <Arduino.h>
#include <FlashStorage_STM32.h>

// Slot byte offsets in flash address space
static const size_t SLOT_A_MAGIC_OFF = 0;
static const size_t SLOT_A_DATA_OFF  = 2;
static const size_t SLOT_B_MAGIC_OFF = 2 + sizeof(AeonState);
static const size_t SLOT_B_DATA_OFF  = 4 + sizeof(AeonState);

// ── CRC32 (IEEE 802.3 poly, same as checkpoint_crc32 in legacy code) ─────────
uint32_t StorageManager::crc32(const uint8_t* data, size_t len) {
    uint32_t crc = 0xFFFFFFFF;
    for (size_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (uint8_t j = 0; j < 8; j++) {
            crc = (crc & 1) ? (crc >> 1) ^ 0xEDB88320 : (crc >> 1);
        }
    }
    return ~crc;
}

// ── Slot I/O ──────────────────────────────────────────────────────────────────
bool StorageManager::writeSlot(uint8_t slot, AeonState* state) {
    size_t magicOff = (slot == 0) ? SLOT_A_MAGIC_OFF : SLOT_B_MAGIC_OFF;
    size_t dataOff  = (slot == 0) ? SLOT_A_DATA_OFF  : SLOT_B_DATA_OFF;

    // Recompute CRC (field crc32 must be zeroed before computing)
    state->crc32 = 0;
    state->crc32 = crc32(reinterpret_cast<const uint8_t*>(state), sizeof(AeonState));

    uint16_t magic = STORAGE_MAGIC;
    EEPROM.put(magicOff, magic);
    EEPROM.put(dataOff, *state);

#if defined(EEPROM_EMULATION_SIZE)
    // FlashStorage_STM32 requires explicit commit
    EEPROM.commit();
#endif
    return true;
}

bool StorageManager::readSlot(uint8_t slot, AeonState* out) {
    size_t magicOff = (slot == 0) ? SLOT_A_MAGIC_OFF : SLOT_B_MAGIC_OFF;
    size_t dataOff  = (slot == 0) ? SLOT_A_DATA_OFF  : SLOT_B_DATA_OFF;

    uint16_t magic = 0;
    EEPROM.get(magicOff, magic);
    if (magic != STORAGE_MAGIC) return false;

    AeonState tmp;
    EEPROM.get(dataOff, tmp);

    uint32_t savedCrc = tmp.crc32;
    tmp.crc32 = 0;
    uint32_t calcCrc = crc32(reinterpret_cast<const uint8_t*>(&tmp), sizeof(AeonState));

    if (savedCrc != calcCrc) return false;

    tmp.crc32 = savedCrc;
    *out = tmp;
    return true;
}

// ── Public API ────────────────────────────────────────────────────────────────
void StorageManager::init() {
#if defined(EEPROM_EMULATION_SIZE)
    EEPROM.begin();
#endif
    _ready = true;
}

bool StorageManager::save(AeonState* state) {
    if (!_ready || !state) return false;

    state->checkpoint_id++;
    // Alternate slots for wear levelling
    _activeSlot = (_activeSlot == 0) ? 1 : 0;
    return writeSlot(_activeSlot, state);
}

bool StorageManager::restore(AeonState* state) {
    if (!_ready || !state) return false;

    AeonState a, b;
    bool okA = readSlot(0, &a);
    bool okB = readSlot(1, &b);

    if (okA && okB) {
        // Both valid — use whichever has the higher checkpoint_id
        if (a.checkpoint_id >= b.checkpoint_id) {
            *state = a;
            _activeSlot = 0;
        } else {
            *state = b;
            _activeSlot = 1;
        }
        return true;
    }
    if (okA) { *state = a; _activeSlot = 0; return true; }
    if (okB) { *state = b; _activeSlot = 1; return true; }

    return false; // Both slots invalid
}

void StorageManager::resetToDefaults(AeonState* state) {
    if (!state) return;
    applyDefaults(state);
    writeSlot(0, state);
    writeSlot(1, state);
    _activeSlot = 0;
}

void StorageManager::applyDefaults(AeonState* state) {
    state->checkpoint_id        = 0;
    state->seq                  = 0;
    state->timestamp            = 0;
    state->model_v              = DEFAULT_MODEL_V;
    state->mean                 = DEFAULT_MEAN;
    state->std_dev              = DEFAULT_STD_DEV;
    state->theta                = DEFAULT_THETA;
    state->active_policy_hash   = 0;
    state->deployment_id        = 0;

    // ── Runtime statistics (v3 fields) ────────────────────────────────────────
    state->inference_count      = 0;
    state->avg_confidence_x100  = 0;
    state->avg_latency_ms       = 0;
    state->error_count          = 0;
    state->model_score_x100     = 0;
    state->rollback_count       = 0;
    state->_pad1                = 0;

    // ── Learning buffer metadata (v3 fields) ──────────────────────────────────
    state->learning_buffer_head  = 0;
    state->learning_buffer_count = 0;

    // ── User Profile preferences (v4 fields) ──────────────────────────────────
    state->preferred_temp        = 21.0f;
    state->profile_version       = 0;

    state->crc32                = 0;
}

