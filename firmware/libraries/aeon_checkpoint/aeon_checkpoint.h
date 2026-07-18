/**
 * aeon_checkpoint.h — EEPROM state persistence for power-loss recovery.
 *
 * Layout (EEPROM address 0):
 *   [MAGIC:4][VERSION:1][STATE:sizeof(AeonState)][CRC16:2]
 *
 * On every save the checkpoint_id is incremented so the host can detect gaps.
 * Two alternating slots are used (ping-pong) to protect against partial writes.
 */

#pragma once
#include "aeon_protocol.h"
#include <stdint.h>
#include <stdbool.h>

#define CHECKPOINT_MAGIC    0xAE4E4F4EUL  // ÆON in ASCII
#define CHECKPOINT_VERSION  1
#define CHECKPOINT_SLOT_A   0
#define CHECKPOINT_SLOT_B   64   // offset in EEPROM bytes

/** Attempt to restore state from the newest valid EEPROM slot.
 *  Returns true if a valid checkpoint was found and loaded. */
bool checkpoint_restore(AeonState* state);

/** Save state to the next available EEPROM slot. */
void checkpoint_save(AeonState* state);

/** Zero-initialise state (used on cold start). */
void checkpoint_reset(AeonState* state);
