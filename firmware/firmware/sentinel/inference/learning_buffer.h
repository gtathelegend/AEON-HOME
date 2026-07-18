/**
 * learning_buffer.h — On-device ring buffer for learning data collection.
 *
 * Records inference inputs and outputs for future retraining on the Snapdragon.
 * The firmware NEVER trains — it only collects labeled samples and flushes
 * them to the backend over WebSocket.
 *
 * Design:
 *   - Fixed-size ring buffer (LEARNING_BUFFER_CAPACITY entries)
 *   - Each LearningRecord is a compact snapshot (no dynamic allocation)
 *   - Head/count are persisted in AeonState for power-loss recovery
 *   - Periodic flush sends JSON batch to the backend
 *   - Manual overrides are flagged for higher-quality labeling
 *
 * JSON format for each flushed record:
 *   {
 *     "typ": "learning_record",
 *     "ts": <uint32_t millis>,
 *     "seq": <uint32_t>,
 *     "features": [f0, f1, f2, f3, f4, f5, f6],
 *     "prediction": 0|1,
 *     "confidence": 0.0–1.0,
 *     "override": true|false
 *   }
 */
#pragma once
#include <Arduino.h>
#include "../storage/runtime_state.h"
#include "../communication/transport.h"
#include "../runtime/runtime_config.h"

struct LearningRecord {
    uint32_t timestamp_ms;                    // millis() at capture time
    uint32_t seq;                             // Frame sequence number
    float    features[FEATURE_VECTOR_LEN];   // Sensor feature vector
    uint8_t  prediction;                      // Model output (0 = no presence, 1 = presence)
    uint16_t confidence_x100;                 // Confidence * 100 (0–10000)
    bool     manual_override;                 // True if user corrected this prediction
};

class LearningBuffer {
public:
    LearningBuffer();

    /** Initialize and restore head/count from AeonState. */
    void init(const AeonState* state);

    /**
     * Append a new learning record to the ring buffer.
     * Overwrites oldest record on overflow (ring semantics).
     */
    void append(const LearningRecord& record);

    /**
     * Flush all pending records to the backend via transport.
     * Sends one JSON message per record. Resets count to 0 after flush.
     *
     * @param transport   Active ITransport instance for sending
     * @param state       AeonState pointer for persisting updated head/count
     */
    void flush(ITransport& transport, AeonState* state);

    /** Persist head and count to AeonState. */
    void persist(AeonState* state) const;

    /** Restore head and count from AeonState. */
    void restore(const AeonState* state);

    /** Returns number of records currently buffered. */
    uint16_t count() const { return _count; }

    /** Returns buffer capacity. */
    uint16_t capacity() const { return LEARNING_BUFFER_CAPACITY; }

private:
    LearningRecord _buffer[LEARNING_BUFFER_CAPACITY];
    uint16_t       _head;    // Write position (next slot to write)
    uint16_t       _count;   // Number of valid records

    void _serializeRecord(const LearningRecord& r, char* buf, size_t buf_len) const;
};
