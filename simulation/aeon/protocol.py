"""Wire protocol: message builders and HMAC-SHA256 signing.

Every message on every hop is signed. A leaf switches a real appliance, so it
verifies before acting -- an unsigned command on the home WiFi is how a stranger
turns the AC on at 3 AM.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time

# Demo default. Override with AEON_HMAC_KEY in the environment; the node, the PC
# and every leaf must share it.
_DEFAULT_KEY = b"aeon-home-demo-key-change-me"
HMAC_KEY = os.environ.get("AEON_HMAC_KEY", "").encode() or _DEFAULT_KEY

NODE_ISS = "node:uno-q-01"


def canonical(payload: dict) -> bytes:
    """Signing input: the message minus its own signature, key-sorted, compact.

    Sorting matters -- dict order is not stable across the phone, the PC and the
    node, and an unstable canonical form means every signature fails verification
    for reasons that look like a network bug.
    """
    body = {k: v for k, v in payload.items() if k != "sig"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def sign(payload: dict) -> dict:
    """Return a copy of payload carrying a valid `sig`."""
    signed = {k: v for k, v in payload.items() if k != "sig"}
    signed["sig"] = hmac.new(HMAC_KEY, canonical(signed), hashlib.sha256).hexdigest()
    return signed


def verify(payload: dict) -> bool:
    """True if the message carries a signature we produced over exactly this body."""
    got = payload.get("sig")
    if not isinstance(got, str) or not got:
        return False
    want = hmac.new(HMAC_KEY, canonical(payload), hashlib.sha256).hexdigest()
    return hmac.compare_digest(got, want)


def reject(reason: str) -> dict:
    return {"status": "rejected", "reason": reason}


# --- message builders (numbered as in the message table) -------------------


def command(device: str, on: bool, level: float | None, spoken: str = "",
            ts: float | None = None, hour_start: int = 0, hour_end: int = 24,
            day_type: str = "all") -> dict:
    """1. Phone -> Central. A spoken preference, with the window it describes."""
    return sign({
        "typ": "command",
        "device": device,
        "on": on,
        "level": level,
        "spoken": spoken,
        "ts": ts if ts is not None else time.time(),
        "hour_start": hour_start,
        "hour_end": hour_end,
        "day_type": day_type,
    })


def actuate(device: str, on: bool, level: float | None, src: str) -> dict:
    """2/7. Central -> Leaf. src is `phone` or `model`."""
    return sign({
        "typ": "actuate",
        "device": device,
        "on": on,
        "level": level,
        "src": src,
    })


def leaf_ack(device: str, on: bool, level: float | None, changed: bool) -> dict:
    """3. Leaf -> Central. What the appliance actually did."""
    return sign({
        "typ": "leaf_ack",
        "device": device,
        "on": on,
        "level": level,
        "changed": changed,
    })


def preference(device: str, on: bool, level: float | None, spoken: str, ts: float,
               hour_start: int = 0, hour_end: int = 24, day_type: str = "all",
               src: str = "phone") -> dict:
    """4. Central -> PC. The same command, now as training data.

    Carries the window, not just the instant: "at 9 PM" describes every day, and
    a row without its window cannot be superseded by a later one covering it.
    """
    return sign({
        "typ": "preference",
        "device": device,
        "on": on,
        "level": level,
        "spoken": spoken,
        "ts": ts,
        "hour_start": hour_start,
        "hour_end": hour_end,
        "day_type": day_type,
        "src": src,
    })


def policy_update(model_v: int, sha256: str, size_bytes: int, device_order: list[str],
                  level_ranges: dict, ambient_mean: float, ambient_std: float,
                  kind: str = "schedule") -> dict:
    """5. PC -> Central. The manifest; the blob follows as a framed chunk.

    Carries level_ranges, device_order and the ambient normalisation constants so
    the node denormalises exactly as the PC did in training.
    """
    return sign({
        "typ": "policy_update",
        "model_v": model_v,
        "sha256": sha256,
        "size_bytes": size_bytes,
        "device_order": device_order,
        "level_ranges": level_ranges,
        "ambient_mean": ambient_mean,
        "ambient_std": ambient_std,
        "kind": kind,
    })


def telemetry(temp_c: float, rh_pct: float, motion: int, device_states: dict, model_v: int, ts: float) -> dict:
    """8. Central -> PC. Spooled to eMMC if the PC is unreachable."""
    return sign({
        "iss": NODE_ISS,
        "typ": "telemetry",
        "temp_c": round(temp_c, 1),
        "rh_pct": round(rh_pct, 1),
        "motion": motion,
        "devices": device_states,
        "ts": ts,
        "model_v": model_v,
    })


def usage(device: str, on: bool, level: float | None, occupied: bool,
          src: str, ts: float) -> dict:
    """What the appliance actually did, and when.

    Phase 3 trains on these rows, so they record the state read back from the
    leaf rather than the state the policy asked for. Off steps carry level=None:
    writing the policy's raw level for an off step poisons the lag window, and
    it does so silently because every individual value still looks plausible.
    """
    return sign({
        "iss": NODE_ISS,
        "typ": "usage",
        "device": device,
        "on": on,
        "level": level if on else None,
        "occupied": occupied,
        "src": src,
        "ts": ts,
    })


def manual_action(device: str, on: bool, level: float | None, ts: float) -> dict:
    """The most valuable signal: ground truth about what the user wanted, then."""
    return sign({
        "iss": NODE_ISS,
        "typ": "manual_action",
        "device": device,
        "on": on,
        "level": level,
        "ts": ts,
    })
