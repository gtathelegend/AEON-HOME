/**
 * aeon_protocol.h — Serial framing protocol between Arduino and Snapdragon.
 *
 * Frame format (binary, little-endian):
 *   [MAGIC:2][TYPE:1][SEQ:4][LEN:2][PAYLOAD:LEN][CRC16:2]
 *
 * MAGIC = 0xAE 0x01
 * TYPE  = 0x01 FEATURE_FRAME
 *         0x02 EVENT
 *         0x10 COMMAND (Snapdragon → Arduino)
 *         0xFF ACK
 */

#pragma once
#include <stdint.h>

#define AEON_MAGIC_0   0xAE
#define AEON_MAGIC_1   0x01
#define AEON_MAX_PAYLOAD 256

typedef enum {
  AEON_TYPE_FEATURE_FRAME = 0x01,
  AEON_TYPE_EVENT         = 0x02,
  AEON_TYPE_COMMAND       = 0x10,
  AEON_TYPE_ACK           = 0xFF,
} AeonFrameType;

typedef struct {
  float    temperature;   // °C
  float    humidity;      // %
  uint8_t  motion;        // 0/1
  uint8_t  door_open;     // 0/1
  float    mean_temp;     // rolling mean
  float    var_temp;      // rolling variance
  float    delta_motion;  // motion event rate (events/s)
  uint32_t timestamp_ms;
} FeatureFrame;

typedef struct {
  uint8_t  type;         // AeonFrameType
  uint32_t arg;
  char     payload[128];
} AeonCommand;

typedef struct {
  uint32_t seq;
  uint32_t timestamp;
  uint32_t checkpoint_id;
} AeonState;

// ── API ───────────────────────────────────────────────────────────────────────

/** Send a FeatureFrame to Snapdragon over Serial. */
void protocol_send_frame(const FeatureFrame* frame, uint32_t seq);

/** Send a named event (e.g. boot, power_loss). */
void protocol_send_event(const char* category, const char* name, uint32_t arg);

/** Feed one received byte into the parser state machine. */
void protocol_receive_byte(uint8_t byte);

/** Callback — implement in firmware to handle inbound commands. */
extern void aeon_on_command(const AeonCommand* cmd);
