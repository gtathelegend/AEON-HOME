---
name: aeon-phase-plan
description: ÆON Home build order and the HubState.snapshot() seam that lets phases stack
metadata: 
  node_type: memory
  type: project
  originSessionId: b2a47055-b81b-49a1-b9d6-73933ce7471b
---

Agreed build order for ÆON Home: **Phase 1** dashboard (white bg / black ink, minimalist),
**Phase 2** backend (SQLite, real TCP leaves, eMMC checkpoints, store-and-forward),
**Phase 3** retraining pipeline + Arduino UNO Q deployment.

Phases 1 and 2 are complete and tested as of 2026-07-18 (108 checks across
`tests/test_phase2.py`, `test_endtoend.py`, `test_restart.py`). Phase 2 landed without a
single change to `web/`, which validated the seam.

**Phase 3 entry point:** replace the body of `PCHub.retrain()` in `aeon/pc.py` with a
trained sequence model exported to int8 ONNX. The manifest, sha256 check, `device_order`
check and ack around it already work and need no change. Set `Policy.kind` to
`"int8 ONNX"` so the dashboard stops labelling the artefact a schedule.

The seam that makes this work is `HubState.snapshot()` in `aeon/hubstate.py` — a single
JSON state object that both screens render from. Phase 1 fills it from
`aeon/demo_source.py` (a scripted house); Phase 2 fills the same object from the real
central node. A source must expose `state`, `async run(bcast)`, `async on_message(msg, bcast)`.

Stack decisions made to save hackathon hours: no Node/npm (vanilla HTML/CSS/JS served by
FastAPI), and the phone client is a **web app served over LAN**, not an Android APK.

**Why:** the dashboard must not be rewritten when the real backend lands, and a build step
on ARM64 under time pressure is a liability.

**How to apply:** a source object must expose `state`, `async run(bcast)` and
`async on_message(msg, bcast)`; `run.py --phase` selects which one. Do not modify `web/`
to land backend work. See [[aeon-hackathon-deadline]].

**Measured on this machine** (the design doc's figures are in-process/warm and do not
hold): leaf hop ~1.1 ms median over real TCP, ~1.3 ms with the PC unplugged; cold
checkpoint restore ~12 ms, warm < 1 ms. Quote these, not the doc's 0.60 ms / 0.3 ms.
