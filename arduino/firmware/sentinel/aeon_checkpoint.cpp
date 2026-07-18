#include "aeon_checkpoint.h"
#include <EEPROM.h>

#define EEPROM_BASE_ADDR 0
#define EEPROM_MAGIC     0xAE04

// Local CRC32 for EEPROM validation
static uint32_t checkpoint_crc32(const uint8_t* data, size_t length) {
    uint32_t crc = 0xFFFFFFFF;
    for (size_t i = 0; i < length; i++) {
        crc ^= data[i];
        for (uint8_t j = 0; j < 8; j++) {
            if (crc & 1)
                crc = (crc >> 1) ^ 0xEDB88320;
            else
                crc >>= 1;
        }
    }
    return ~crc;
}

void checkpoint_init() {
    // Some boards require EEPROM.begin(size)
#if defined(ESP8266) || defined(ESP32)
    EEPROM.begin(512);
#endif
}

bool checkpoint_restore(AeonState* state) {
    if (!state) return false;
    
    // Read magic bytes (to see if initialized)
    uint16_t magic = 0;
    EEPROM.get(EEPROM_BASE_ADDR, magic);
    if (magic != EEPROM_MAGIC) {
        return false;
    }
    
    // Read state
    AeonState temp;
    EEPROM.get(EEPROM_BASE_ADDR + 2, temp);
    
    // Verify CRC
    uint32_t saved_crc = temp.crc32;
    temp.crc32 = 0;
    uint32_t calc_crc = checkpoint_crc32((const uint8_t*)&temp, sizeof(AeonState));
    
    if (saved_crc == calc_crc) {
        *state = temp;
        state->crc32 = saved_crc;
        return true;
    }
    return false; // corrupted
}

void checkpoint_save(AeonState* state) {
    if (!state) return;
    
    state->checkpoint_id++;
    state->crc32 = 0;
    state->crc32 = checkpoint_crc32((const uint8_t*)state, sizeof(AeonState));
    
    // Write magic and state
    uint16_t magic = EEPROM_MAGIC;
    EEPROM.put(EEPROM_BASE_ADDR, magic);
    EEPROM.put(EEPROM_BASE_ADDR + 2, *state);
    
#if defined(ESP8266) || defined(ESP32)
    EEPROM.commit();
#endif
}

void checkpoint_reset(AeonState* state) {
    if (!state) return;
    state->checkpoint_id = 0;
    state->seq = 0;
    state->timestamp = 0;
    state->active_policy_hash = 0;
    state->model_v = 1;
    state->mean = 0.0f;
    state->std_dev = 1.0f;
    state->theta = 25.0f;
    state->crc32 = 0;
    checkpoint_save(state);
}
