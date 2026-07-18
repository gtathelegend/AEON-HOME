/**
 * runtime_config.h — Central configuration for ÆON Sentinel on Arduino UNO Q.
 *
 * All constants live here. No magic numbers anywhere else in the firmware.
 *
 * Board:  Arduino UNO Q (STM32U585 MCU, WCBN3536A WiFi)
 * Target: Zephyr RTOS + Arduino API layer
 */
#pragma once

// ── Hardware Pins ─────────────────────────────────────────────────────────────
#define PIN_DHT        2    // DHT11 data pin
#define PIN_PIR        3    // HC-SR501 PIR motion sensor (HIGH = motion)
#define PIN_BUTTON     4    // False alarm button (LOW when pressed, INPUT_PULLUP)
#define PIN_LED        5    // Status / warning LED
#define PIN_RELAY_1    7    // General purpose relay 1
#define PIN_RELAY_2    8    // General purpose relay 2
#define PIN_BUZZER     9    // Piezo buzzer via tone()
#define DHT_TYPE       DHT11

// ── Serial Baud Rates ─────────────────────────────────────────────────────────
#define BAUD_DEBUG     115200  // USB-CDC debug console
#define BAUD_SENSOR    9600    // Reserved for any legacy UART sensor

// ── Scheduler Intervals (milliseconds) ───────────────────────────────────────
#define INTERVAL_SENSOR_MS        500    // Sensor sample & telemetry transmit
#define INTERVAL_CHECKPOINT_MS    2000   // EEPROM flash checkpoint save
#define INTERVAL_HEARTBEAT_MS     5000   // Heartbeat packet (every 10 samples)
#define INTERVAL_HEALTH_MS        10000  // Health status report
#define INTERVAL_DEVICE_POLL_MS   15000  // Device registry liveness poll
#define INTERVAL_DEPLOY_CHECK_MS  30000  // Deployment availability check

// ── Protocol ──────────────────────────────────────────────────────────────────
#define PROTOCOL_VERSION       1
#define DEVICE_ID              "sentinel-01"
#define GATEWAY_ID             "aeon-uno-q-01"
#define FIRMWARE_VERSION       "2.0.0"
#define MAX_JSON_PAYLOAD       512     // Maximum serialized JSON size (bytes)
#define MAX_CMD_PAYLOAD        256     // Maximum inbound command payload

// ── WiFi / WebSocket ──────────────────────────────────────────────────────────
// Credentials live in config.h (git-ignored)
#define WS_PATH                "/ws/device"
#define WS_RECONNECT_INTERVAL  5000   // ms between reconnection attempts
#define WS_MAX_RETRIES         10     // Give up and reboot after N failures
#define WIFI_CONNECT_TIMEOUT   30000  // ms to wait for initial WiFi association

// ── Message Queue ─────────────────────────────────────────────────────────────
#define MSG_QUEUE_SIZE         16     // Offline ring-buffer depth
#define MSG_QUEUE_ENTRY_LEN    512    // Max bytes per queued message

// ── Storage (Flash EEPROM Emulation) ─────────────────────────────────────────
#define STORAGE_MAGIC          0xAE05  // v3: extended AeonState (58 bytes). Rejects old v1/v2 flash.
#define STORAGE_SLOT_A         0       // Primary ping-pong slot index
#define STORAGE_SLOT_B         1       // Secondary ping-pong slot index
#define STORAGE_MAX_WRITES     50000   // STM32U5 enhanced flash write endurance

// ── Feature Extraction ───────────────────────────────────────────────────────
#define FEATURE_WINDOW_SIZE    10      // Rolling statistics sample window

// ── Default Policy Thresholds ────────────────────────────────────────────────
#define DEFAULT_THETA          25.0f   // Default temperature anomaly threshold (°C)
#define DEFAULT_MODEL_V        1       // Initial model version
#define DEFAULT_MEAN           0.0f    // Prior mean (updated by model_update)
#define DEFAULT_STD_DEV        1.0f    // Prior std dev

// ── Boot ──────────────────────────────────────────────────────────────────────
#define BOOT_STAGE_COUNT       13      // Total boot stages in RuntimeManager
#define BOOT_WIFI_TIMEOUT_MS   30000   // Max time to wait for WiFi at boot

// ── Model Scoring Weights ─────────────────────────────────────────────────────
// All weights should sum to 1.0. Stored as floats, configured at compile time.
// Adjust these to tune the composite model quality score.
#define SCORE_W_CONFIDENCE      0.25f  // Raw model output confidence
#define SCORE_W_ACCURACY        0.20f  // Accuracy estimate from training
#define SCORE_W_CORRECTION_RATE 0.15f  // False alarm + override rate (inverted)
#define SCORE_W_LATENCY         0.10f  // Inference latency (inverted, lower=better)
#define SCORE_W_RELIABILITY     0.15f  // 1 - error_rate
#define SCORE_W_ROLLBACK_HIST   0.10f  // Rollback count (inverted)
#define SCORE_W_STABILITY       0.05f  // Variance of recent confidence values

// ── Rollback Thresholds ───────────────────────────────────────────────────────
// Automatic rollback triggers if the runtime composite score drops below
// ROLLBACK_SCORE_THRESHOLD or confidence collapses below ROLLBACK_CONF_THRESHOLD.
#define ROLLBACK_SCORE_THRESHOLD     0.30f  // Composite score below this → rollback
#define ROLLBACK_CONF_THRESHOLD      0.25f  // Avg confidence below this → rollback
#define ROLLBACK_LATENCY_THRESHOLD   500    // Avg latency above this (ms) → rollback
#define ROLLBACK_ERROR_RATE_THRESHOLD 0.30f // Error rate above this → rollback

// ── Statistics Flush ──────────────────────────────────────────────────────────
#define STATISTICS_FLUSH_INTERVAL_MS  60000  // Flush stats to backend every 60 s

// ── Learning Buffer ───────────────────────────────────────────────────────────
#define LEARNING_BUFFER_CAPACITY     128    // Ring buffer depth (LearningRecord count)
#define LEARNING_BUFFER_FLUSH_MS     120000 // Flush learning records every 2 minutes
#define FEATURE_VECTOR_LEN           7      // Must match FeatureCompatibility.feature_vector_size
