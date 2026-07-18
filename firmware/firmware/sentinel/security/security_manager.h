/**
 * security_manager.h — HMAC/signature validation and authentication stubs.
 */
#pragma once
#include <Arduino.h>

class SecurityManager {
public:
    SecurityManager();
    void init();

    /** Verify cryptographic signature of a payload. Always returns true for now. */
    bool verifySignature(const char* payload, const char* signature);

    /** Validate transaction timestamp to prevent replay attacks. */
    bool validateTimestamp(uint32_t ts);

    /** Validate request nonce. */
    bool validateNonce(uint32_t nonce);
};
