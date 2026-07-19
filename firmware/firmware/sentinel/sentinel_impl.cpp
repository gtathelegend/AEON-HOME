/**
 * sentinel_impl.cpp — Unified sketch compilation entry.
 *
 * Includes all C++ implementations from subdirectories so they compile
 * correctly under the Arduino build system (which doesn't traverse subdirectories).
 */

#if defined(ARDUINO_UNO_Q)
#include <stddef.h>
extern "C" {
    static int s_errno_val = 0;
    int* __errno() {
        return &s_errno_val;
    }
    char* strncat(char* dest, const char* src, size_t n) {
        char* d = dest;
        while (*d != '\0') {
            d++;
        }
        while (n > 0 && *src != '\0') {
            *d++ = *src++;
            n--;
        }
        *d = '\0';
        return dest;
    }
}
#endif

#include "runtime/runtime_manager.cpp"
#include "communication/serial_transport.cpp"
#include "communication/wifi_transport.cpp"
#include "communication/message_queue.cpp"
#include "protocols/aeon_protocol.cpp"
#include "protocols/command_router.cpp"
#include "storage/storage_manager.cpp"
#include "checkpoint/checkpoint_manager.cpp"
#include "scheduler/scheduler.cpp"
#include "telemetry/telemetry_manager.cpp"
#include "inference/model_runtime.cpp"
#include "inference/local_policy.cpp"
#include "inference/rollback_manager.cpp"
#include "inference/learning_engine.cpp"
#include "inference/dream_state.cpp"
#include "inference/learning_buffer.cpp"
#include "inference/model_scorer.cpp"
#include "inference/confidence_engine.cpp"
#include "inference/statistics_collector.cpp"
#include "devices/device_registry.cpp"
#include "security/security_manager.cpp"
#include "sensors/sensor_driver.cpp"
#include "features/feature_extractor.cpp"
#include "actuators/actuator_driver.cpp"
#include "health/health_monitor.cpp"
