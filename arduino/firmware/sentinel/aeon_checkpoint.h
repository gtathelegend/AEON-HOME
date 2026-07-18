#ifndef AEON_CHECKPOINT_H
#define AEON_CHECKPOINT_H

#include <Arduino.h>

#pragma pack(push, 1)
struct AeonState {
    uint32_t checkpoint_id;
    uint32_t seq;
    uint32_t timestamp;
    uint32_t active_policy_hash;
    uint32_t model_v;
    float    mean;
    float    std_dev;
    float    theta;
    uint32_t crc32;
};
#pragma pack(pop)

// Initialize EEPROM subsystem
void checkpoint_init();

// Attempt to restore state. Returns true if valid, false if corrupted/empty.
bool checkpoint_restore(AeonState* state);

// Save state to EEPROM
void checkpoint_save(AeonState* state);

// Reset state to defaults
void checkpoint_reset(AeonState* state);

#endif // AEON_CHECKPOINT_H
