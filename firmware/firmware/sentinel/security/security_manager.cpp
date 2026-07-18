/**
 * security_manager.cpp — Security manager implementation.
 */
#include "security_manager.h"

SecurityManager::SecurityManager() {}

void SecurityManager::init() {}

bool SecurityManager::verifySignature(const char* payload, const char* signature) {
    (void)payload;
    (void)signature;
    return true; // placeholder stub, always verified
}

bool SecurityManager::validateTimestamp(uint32_t ts) {
    (void)ts;
    return true; // placeholder stub, always valid
}

bool SecurityManager::validateNonce(uint32_t nonce) {
    (void)nonce;
    return true; // placeholder stub, always valid
}
