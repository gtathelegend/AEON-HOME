/**
 * aeon_checkpoint.cpp — EEPROM ping-pong checkpoint implementation.
 */

#include "aeon_checkpoint.h"
#include <EEPROM.h>
#include <string.h>

// ── CRC-16 (same poly as protocol) ───────────────────────────────────────────
static uint16_t crc16(const uint8_t* d, uint16_t n) {
  uint16_t c = 0xFFFF;
  for (uint16_t i = 0; i < n; i++) {
    c ^= (uint16_t)d[i] << 8;
    for (uint8_t j = 0; j < 8; j++) c = (c & 0x8000) ? (c << 1) ^ 0x1021 : c << 1;
  }
  return c;
}

// ── Slot structure ────────────────────────────────────────────────────────────
typedef struct {
  uint32_t  magic;
  uint8_t   version;
  AeonState state;
  uint16_t  crc;
} Slot;

static const uint16_t SLOTS[2] = { CHECKPOINT_SLOT_A, CHECKPOINT_SLOT_B };

static bool read_slot(uint8_t idx, Slot* out) {
  uint16_t addr = SLOTS[idx];
  uint8_t* p = (uint8_t*)out;
  for (uint16_t i = 0; i < sizeof(Slot); i++) p[i] = EEPROM.read(addr + i);
  if (out->magic != CHECKPOINT_MAGIC)   return false;
  if (out->version != CHECKPOINT_VERSION) return false;
  uint16_t expected = crc16((uint8_t*)&out->state, sizeof(AeonState));
  return out->crc == expected;
}

static void write_slot(uint8_t idx, const Slot* in) {
  uint16_t addr = SLOTS[idx];
  const uint8_t* p = (const uint8_t*)in;
  for (uint16_t i = 0; i < sizeof(Slot); i++) EEPROM.update(addr + i, p[i]);
}

static uint8_t g_active_slot = 0;

bool checkpoint_restore(AeonState* state) {
  Slot s0, s1;
  bool ok0 = read_slot(0, &s0);
  bool ok1 = read_slot(1, &s1);
  if (!ok0 && !ok1) return false;
  Slot* best = (!ok0) ? &s1 : (!ok1) ? &s0
             : (s0.state.checkpoint_id >= s1.state.checkpoint_id ? &s0 : &s1);
  *state = best->state;
  g_active_slot = (best == &s0) ? 0 : 1;
  return true;
}

void checkpoint_save(AeonState* state) {
  state->checkpoint_id++;
  g_active_slot ^= 1;   // alternate slots
  Slot s;
  s.magic   = CHECKPOINT_MAGIC;
  s.version = CHECKPOINT_VERSION;
  s.state   = *state;
  s.crc     = crc16((uint8_t*)&s.state, sizeof(AeonState));
  write_slot(g_active_slot, &s);
}

void checkpoint_reset(AeonState* state) {
  memset(state, 0, sizeof(AeonState));
}
