/**
 * scheduler.h — Central cooperative scheduler.
 */
#pragma once
#include <Arduino.h>

class Scheduler {
public:
    typedef void (*TaskCallback)(void* context);

    struct ScheduledTask {
        unsigned long interval_ms;
        unsigned long last_ms;
        TaskCallback callback;
        void* context;
        bool enabled;
    };

    Scheduler();
    void init();

    /** Register a periodic task. Returns index/id on success, -1 on failure. */
    int registerTask(unsigned long interval_ms, TaskCallback callback, void* context);

    /** Drive the scheduler. Checks each task and runs it if overdue. */
    void tick();

    /** Enable/disable a task by index. */
    void setTaskEnabled(uint8_t index, bool enabled);

private:
    static const uint8_t MAX_TASKS = 8;
    ScheduledTask _tasks[MAX_TASKS];
    uint8_t _task_count;
};
