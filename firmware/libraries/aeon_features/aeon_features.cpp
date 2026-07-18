/**
 * aeon_features.cpp — Rolling-window feature extraction.
 *
 * Maintains a circular buffer of FEATURE_WINDOW sensor readings and
 * computes per-channel mean, variance, and delta each time a new
 * reading is ingested.
 *
 * All arithmetic is done in float32 — sufficient precision, minimal
 * RAM footprint on AVR/ARM targets.
 */

#include "aeon_features.h"
#include <string.h>
#include <math.h>

// ── Circular buffer ───────────────────────────────────────────────────────────
static float  g_temp_buf[FEATURE_WINDOW];
static uint8_t g_fill = 0;        // how many valid samples in the buffer
static uint8_t g_head = 0;        // next write index
static uint32_t g_motion_events = 0;
static uint32_t g_window_start_ms = 0;
static uint8_t g_prev_motion = 0;

void features_init(void) {
  memset(g_temp_buf, 0, sizeof(g_temp_buf));
  g_fill            = 0;
  g_head            = 0;
  g_motion_events   = 0;
  g_window_start_ms = millis();
  g_prev_motion     = 0;
}

void features_update(FeatureFrame* frame, const SensorReading* r) {
  // ── Temperature rolling stats ─────────────────────────────────────────────
  g_temp_buf[g_head] = r->temperature;
  g_head = (g_head + 1) % FEATURE_WINDOW;
  if (g_fill < FEATURE_WINDOW) g_fill++;

  // Welford online mean + variance
  float mean = 0.0f, M2 = 0.0f;
  for (uint8_t i = 0; i < g_fill; i++) {
    float x = g_temp_buf[i];
    float delta = x - mean;
    mean += delta / (i + 1);
    M2   += delta * (x - mean);
  }
  float variance = (g_fill > 1) ? M2 / (g_fill - 1) : 0.0f;

  // ── Motion event rate ─────────────────────────────────────────────────────
  if (r->motion && !g_prev_motion) g_motion_events++;   // rising edge
  g_prev_motion = r->motion;

  uint32_t window_ms = r->timestamp_ms - g_window_start_ms;
  float delta_motion = (window_ms > 0)
      ? (float)g_motion_events / (window_ms / 1000.0f)
      : 0.0f;

  // Reset motion window every FEATURE_WINDOW samples
  if (g_fill == FEATURE_WINDOW) {
    g_motion_events   = 0;
    g_window_start_ms = r->timestamp_ms;
  }

  // ── Populate frame ────────────────────────────────────────────────────────
  frame->temperature   = r->temperature;
  frame->humidity      = r->humidity;
  frame->motion        = r->motion;
  frame->door_open     = r->door_open;
  frame->mean_temp     = mean;
  frame->var_temp      = variance;
  frame->delta_motion  = delta_motion;
  frame->timestamp_ms  = r->timestamp_ms;
}
