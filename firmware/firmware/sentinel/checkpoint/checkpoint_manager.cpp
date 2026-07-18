/**
 * checkpoint_manager.cpp — High-level checkpoint API implementation.
 */
#include "checkpoint_manager.h"
#include <Arduino.h>

CheckpointManager::CheckpointManager(StorageManager& storageManager)
    : _storage(storageManager) {}

void CheckpointManager::init() {
    // Storage manager should already be initialized by RuntimeManager
}

bool CheckpointManager::restore(AeonState* state) {
    if (!state) return false;
    return _storage.restore(state);
}

bool CheckpointManager::save(AeonState* state) {
    if (!state) return false;
    return _storage.save(state);
}

void CheckpointManager::reset(AeonState* state) {
    if (!state) return;
    _storage.resetToDefaults(state);
}
