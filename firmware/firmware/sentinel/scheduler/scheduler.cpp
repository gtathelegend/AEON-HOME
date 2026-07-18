/**
 * scheduler.cpp — Cooperative scheduler implementation.
 */
#include "scheduler.h"

Scheduler::Scheduler()
    : _task_count(0) {}

void Scheduler::init() {
    _task_count = 0;
}

int Scheduler::registerTask(unsigned long interval_ms, TaskCallback callback, void* context) {
    if (_task_count >= MAX_TASKS || !callback) return -1;

    _tasks[_task_count].interval_ms = interval_ms;
    _tasks[_task_count].last_ms = millis();
    _tasks[_task_count].callback = callback;
    _tasks[_task_count].context = context;
    _tasks[_task_count].enabled = true;

    return _task_count++;
}

void Scheduler::tick() {
    unsigned long now = millis();

    for (uint8_t i = 0; i < _task_count; i++) {
        if (!_tasks[i].enabled) continue;

        if (now - _tasks[i].last_ms >= _tasks[i].interval_ms) {
            // Update last execution time
            _tasks[i].last_ms = now;
            // Execute task callback
            _tasks[i].callback(_tasks[i].context);
        }
    }
}

void Scheduler::setTaskEnabled(uint8_t index, bool enabled) {
    if (index < _task_count) {
        _tasks[index].enabled = enabled;
    }
}
