/**
 * storage_manager.h — Sole flash/EEPROM gatekeeper for ÆON Sentinel.
 *
 * On Arduino UNO Q (STM32U585), there is no dedicated EEPROM.
 * All non-volatile storage is provided by Flash EEPROM emulation
 * via the FlashStorage_STM32 library.
 *
 * Design:
 *   - Dual-slot ping-pong write to maximise flash endurance.
 *   - CRC32 validation on every read.
 *   - Only this class may call FlashStorage / EEPROM primitives.
 *   - All other modules access state through CheckpointManager.
 */
#pragma once
#include "runtime_state.h"

class StorageManager {
public:
    /** One-time initialization. Must be called before any other method. */
    void init();

    /**
     * Save state to flash using ping-pong slot rotation.
     * Increments checkpoint_id, computes CRC32, writes to next slot.
     * Returns true on success.
     */
    bool save(AeonState* state);

    /**
     * Attempt to restore state from flash.
     * Validates magic marker and CRC32. Tries slot A, then slot B.
     * Returns true if a valid state was found and loaded into *state.
     */
    bool restore(AeonState* state);

    /**
     * Reset to factory defaults and write to both slots.
     * Called when restore() fails and we need a clean start.
     */
    void resetToDefaults(AeonState* state);

    /**
     * Returns true if the storage layer has been successfully initialized.
     */
    bool isReady() const { return _ready; }

private:
    bool    _ready      = false;
    uint8_t _activeSlot = 0;   // 0 = slot A, 1 = slot B

    static uint32_t crc32(const uint8_t* data, size_t len);
    bool writeSlot(uint8_t slot, AeonState* state);
    bool readSlot(uint8_t slot, AeonState* out);
    void applyDefaults(AeonState* state);
};
