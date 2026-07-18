#ifndef AEON_PROTOCOL_H
#define AEON_PROTOCOL_H

#include <Arduino.h>
#include "aeon_features.h"
#include "aeon_sensors.h"
#include "aeon_checkpoint.h"

// ── API ───────────────────────────────────────────────────────────────────────

/** Initialise serial. */
void protocol_init(uint32_t debug_baud_rate, uint32_t esp_baud_rate);

/** Send a raw JSON string event */
void protocol_send_raw(const char* json);

/** Send a heartbeat event */
void protocol_send_heartbeat(uint32_t seq, uint32_t model_v);

/** Send a sensor update event */
void protocol_send_sensor_update(const SensorReading* reading, uint32_t seq, uint32_t model_v);

/** Feed one received byte into the parser state machine. */
void protocol_receive_byte(uint8_t byte);

/** Check for and process incoming bytes from ESP UART */
void protocol_update();

/** Callback — implement in firmware to handle inbound JSON commands. */
extern "C" void aeon_on_command(const char* json_str);

#endif // AEON_PROTOCOL_H

