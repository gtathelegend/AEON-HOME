/**
 * message_queue.cpp — Message queue implementation.
 */
#include "message_queue.h"
#include <string.h>

MessageQueue::MessageQueue()
    : _head(0), _tail(0), _size(0) {}

void MessageQueue::init() {
    clear();
}

bool MessageQueue::enqueue(const char* payload) {
    if (!payload) return false;

    if (isFull()) {
        // Drop oldest message to make room (overwrite head)
        _head = (_head + 1) % MSG_QUEUE_SIZE;
        _size--;
    }

    strncpy(_queue[_tail].payload, payload, MSG_QUEUE_ENTRY_LEN - 1);
    _queue[_tail].payload[MSG_QUEUE_ENTRY_LEN - 1] = '\0';
    _queue[_tail].retry_count = 0;
    _queue[_tail].last_attempt_ms = 0;

    _tail = (_tail + 1) % MSG_QUEUE_SIZE;
    _size++;
    return true;
}

bool MessageQueue::dequeue(char* buf_out) {
    if (isEmpty()) return false;

    if (buf_out) {
        strcpy(buf_out, _queue[_head].payload);
    }

    _head = (_head + 1) % MSG_QUEUE_SIZE;
    _size--;
    return true;
}

bool MessageQueue::peek(char* buf_out) {
    if (isEmpty()) return false;

    if (buf_out) {
        strcpy(buf_out, _queue[_head].payload);
    }
    return true;
}

void MessageQueue::clear() {
    _head = 0;
    _tail = 0;
    _size = 0;
}
