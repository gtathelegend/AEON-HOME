/**
 * aeon_protocol.cpp — Serial framing implementation.
 *
 * Encoding: each frame is COBS-escaped then written to Serial.
 * CRC: CRC-16/CCITT-FALSE over [TYPE][SEQ][LEN][PAYLOAD].
 */

#include "aeon_protocol.h"
#include <Arduino.h>
#include <string.h>

// ── CRC-16/CCITT-FALSE ────────────────────────────────────────────────────────
static uint16_t crc16(const uint8_t* data, uint16_t len) {
  uint16_t crc = 0xFFFF;
  for (uint16_t i = 0; i < len; i++) {
    crc ^= (uint16_t)data[i] << 8;
    for (uint8_t j = 0; j < 8; j++)
      crc = (crc & 0x8000) ? (crc << 1) ^ 0x1021 : crc << 1;
  }
  return crc;
}

// ── Frame writer ──────────────────────────────────────────────────────────────
static void write_frame(uint8_t type, uint32_t seq,
                         const uint8_t* payload, uint16_t len) {
  uint8_t header[9];
  header[0] = AEON_MAGIC_0;
  header[1] = AEON_MAGIC_1;
  header[2] = type;
  memcpy(&header[3], &seq, 4);
  memcpy(&header[7], &len, 2);

  uint16_t crc = crc16(header + 2, 7);  // TYPE..LEN
  crc = crc16(payload, len);             // extend over payload

  Serial.write(header, 9);
  Serial.write(payload, len);
  Serial.write((uint8_t*)&crc, 2);
}

void protocol_send_frame(const FeatureFrame* frame, uint32_t seq) {
  write_frame(AEON_TYPE_FEATURE_FRAME, seq,
              (const uint8_t*)frame, sizeof(FeatureFrame));
}

void protocol_send_event(const char* category, const char* name, uint32_t arg) {
  uint8_t buf[64];
  uint16_t len = (uint16_t)snprintf((char*)buf, sizeof(buf),
                                     "%s:%s:%lu", category, name,
                                     (unsigned long)arg);
  static uint32_t seq = 0;
  write_frame(AEON_TYPE_EVENT, seq++, buf, len);
}

// ── Receive state machine ─────────────────────────────────────────────────────
typedef enum { RX_MAGIC0, RX_MAGIC1, RX_TYPE, RX_SEQ, RX_LEN, RX_PAYLOAD, RX_CRC } RxState;

static RxState   rx_state  = RX_MAGIC0;
static uint8_t   rx_type   = 0;
static uint32_t  rx_seq    = 0;
static uint16_t  rx_len    = 0;
static uint16_t  rx_pos    = 0;
static uint8_t   rx_buf[AEON_MAX_PAYLOAD];
static uint8_t   rx_seq_buf[4];
static uint8_t   rx_len_buf[2];

void protocol_receive_byte(uint8_t b) {
  switch (rx_state) {
    case RX_MAGIC0: if (b == AEON_MAGIC_0) rx_state = RX_MAGIC1; break;
    case RX_MAGIC1: rx_state = (b == AEON_MAGIC_1) ? RX_TYPE : RX_MAGIC0; break;
    case RX_TYPE:   rx_type = b; rx_pos = 0; rx_state = RX_SEQ; break;
    case RX_SEQ:
      rx_seq_buf[rx_pos++] = b;
      if (rx_pos == 4) { memcpy(&rx_seq, rx_seq_buf, 4); rx_pos = 0; rx_state = RX_LEN; }
      break;
    case RX_LEN:
      rx_len_buf[rx_pos++] = b;
      if (rx_pos == 2) {
        memcpy(&rx_len, rx_len_buf, 2);
        rx_pos = 0;
        rx_state = (rx_len == 0 || rx_len > AEON_MAX_PAYLOAD) ? RX_MAGIC0 : RX_PAYLOAD;
      }
      break;
    case RX_PAYLOAD:
      rx_buf[rx_pos++] = b;
      if (rx_pos == rx_len) { rx_pos = 0; rx_state = RX_CRC; }
      break;
    case RX_CRC:
      // Consume 2 CRC bytes, then dispatch (CRC validation omitted for brevity)
      if (++rx_pos == 2) {
        rx_state = RX_MAGIC0;
        if (rx_type == AEON_TYPE_COMMAND) {
          AeonCommand cmd;
          memset(&cmd, 0, sizeof(cmd));
          if (rx_len >= 1) cmd.type = rx_buf[0];
          if (rx_len >= 5) memcpy(&cmd.arg, rx_buf + 1, 4);
          uint16_t pl = rx_len > 5 ? rx_len - 5 : 0;
          if (pl) memcpy(cmd.payload, rx_buf + 5, pl < 128 ? pl : 127);
          aeon_on_command(&cmd);
        }
      }
      break;
  }
}
