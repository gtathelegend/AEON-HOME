/**
 * checkpoint_manager.h — High-level checkpoint API.
 *
 * Implements high-level recovery and persistence logic.
 * Interacts with StorageManager to read and write states.
 */
#pragma once
#include "../storage/storage_manager.h"
#include "../storage/runtime_state.h"

class CheckpointManager {
public:
    CheckpointManager(StorageManager& storageManager);

    /** Initialize the checkpoint system. */
    void init();

    /**
     * Restore state from persistence.
     * Returns true if loaded from flash, false if defaulted.
     */
    bool restore(AeonState* state);

    /** Save the current state to flash. */
    bool save(AeonState* state);

    /** Reset state to factory defaults. */
    void reset(AeonState* state);

private:
    StorageManager& _storage;
};
