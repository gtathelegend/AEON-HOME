/**
 * learning_buffer.cpp — LearningBuffer ring buffer implementation.
 */
#include "learning_buffer.h"
#include <string.h>
#include <stdio.h>

LearningBuffer::LearningBuffer()
    : _head(0), _count(0)
{
    memset(_buffer, 0, sizeof(_buffer));
}

void LearningBuffer::init(const AeonState* state) {
    memset(_buffer, 0, sizeof(_buffer));
    _head  = 0;
    _count = 0;
    if (state) restore(state);
}

void LearningBuffer::append(const LearningRecord& record) {
    _buffer[_head] = record;
    _head = (_head + 1) % LEARNING_BUFFER_CAPACITY;
    if (_count < LEARNING_BUFFER_CAPACITY) {
        _count++;
    }
    // When count == capacity, _head has already overwritten the oldest entry
    // (ring semantics: oldest is silently discarded)
}

void LearningBuffer::flush(IAeonTransport& transport, AeonState* state) {
    if (_count == 0) return;

    // Determine start index for ordered traversal
    // If buffer is not full, start at 0; if full, oldest is at _head
    uint16_t start = (_count < LEARNING_BUFFER_CAPACITY) ? 0 : _head;
    char buf[MAX_JSON_PAYLOAD];

    for (uint16_t i = 0; i < _count; i++) {
        uint16_t idx = (start + i) % LEARNING_BUFFER_CAPACITY;
        _serializeRecord(_buffer[idx], buf, sizeof(buf));
        transport.send(buf);
    }

    // Reset after flush
    _count = 0;
    _head  = 0;

    persist(state);

    Serial.print("[LearningBuffer] Flushed records.");
}

void LearningBuffer::persist(AeonState* state) const {
    if (!state) return;
    state->learning_buffer_head  = _head;
    state->learning_buffer_count = _count;
}

void LearningBuffer::restore(const AeonState* state) {
    if (!state) return;
    // Note: actual record bytes are not stored in AeonState (too large).
    // Only head/count survive a reboot. The buffer contents are lost,
    // but count is preserved so the firmware knows data was pending.
    _head  = state->learning_buffer_head  % LEARNING_BUFFER_CAPACITY;
    _count = state->learning_buffer_count;
    if (_count > LEARNING_BUFFER_CAPACITY) {
        _count = 0;  // Corrupt value — reset safely
        _head  = 0;
    }
}

void LearningBuffer::_serializeRecord(
    const LearningRecord& r, char* buf, size_t buf_len) const
{
    // Build feature array string
    char feat_str[128] = "[";
    for (uint8_t i = 0; i < FEATURE_VECTOR_LEN; i++) {
        char tmp[16];
        snprintf(tmp, sizeof(tmp), "%.4f", (double)r.features[i]);
        strncat(feat_str, tmp, sizeof(feat_str) - strlen(feat_str) - 1);
        if (i < FEATURE_VECTOR_LEN - 1) {
            strncat(feat_str, ",", sizeof(feat_str) - strlen(feat_str) - 1);
        }
    }
    strncat(feat_str, "]", sizeof(feat_str) - strlen(feat_str) - 1);

    snprintf(buf, buf_len,
        "{\"typ\":\"learning_record\","
        "\"ts\":%lu,"
        "\"seq\":%lu,"
        "\"features\":%s,"
        "\"prediction\":%u,"
        "\"confidence\":%.4f,"
        "\"override\":%s}",
        (unsigned long)r.timestamp_ms,
        (unsigned long)r.seq,
        feat_str,
        (unsigned)r.prediction,
        (double)(r.confidence_x100 / 100.0f),
        r.manual_override ? "true" : "false"
    );
}
