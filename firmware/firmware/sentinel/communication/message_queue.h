/**
 * message_queue.h — Retry queue and reliability layer.
 */
#pragma once
#include "../runtime/runtime_config.h"

struct QueuedMessage {
    char payload[MSG_QUEUE_ENTRY_LEN];
    uint8_t retry_count;
    unsigned long last_attempt_ms;
};

class MessageQueue {
public:
    MessageQueue();
    void init();

    /** Enqueue a message to be sent. */
    bool enqueue(const char* payload);

    /** Dequeue the oldest message. */
    bool dequeue(char* buf_out);

    /** Peek at the oldest message. */
    bool peek(char* buf_out);

    /** Clear the queue. */
    void clear();

    uint16_t size() const { return _size; }
    bool isFull() const { return _size == MSG_QUEUE_SIZE; }
    bool isEmpty() const { return _size == 0; }

private:
    QueuedMessage _queue[MSG_QUEUE_SIZE];
    uint16_t _head;
    uint16_t _tail;
    uint16_t _size;
};
