/**
 * message_envelope.h — Standard message envelope structure.
 */
#pragma once
#include <stdint.h>

struct MessageEnvelope {
    uint32_t message_id;
    uint32_t timestamp;
    char     source[16];
    char     destination[16];
    uint8_t  protocol_version;
    char     message_type[32];
    char     signature[32];
    uint8_t  priority;
    uint8_t  retry_counter;
};
