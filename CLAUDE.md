# ÆON Home — working notes for Claude Code

Read this first. It is the development context, carried in the repo so it
survives moving between machines. Claude Code loads it automatically.

**Hackathon:** Snapdragon Multiverse, Qualcomm Noida. Submission deadline
**2026-07-19 13:00 IST**, demo is **5 minutes, hard-timed**. Judging: Technical
Implementation 40 / Use-Case & Innovation 25 / Deployment & Accessibility 20 /
Presentation & Docs 15, plus a separate 100-point Multi-Device Orchestration
prize — which is the natural fit for the phone → node → leaf + PC fan-out.

Submission requires a **public GitHub repo** with README, team names and emails,
setup-from-scratch instructions, an open-source licence, and the app must be
runnable from those instructions.

---

## What this is

Speak a preference once — *"Set the AC to 25 degrees at 9 PM."* The central node
switches the appliance immediately and forwards the same sentence to the AI PC,
which learns it. No cloud in the control loop.

```
Phone ──► CENTRAL NODE ──1──► targeted leaf   (the appliance responds NOW)
                        └─2──► PC              (the preference becomes training data)
```

The order is the design: the person comes first. Neither failure may break the
other — PC offline still actuates and spools; leaf offline still learns.

| Role | | Can it be switched off? |
|---|---|---|
| AI PC | trains, holds SQLite | yes — the house keeps running |
| Arduino UNO Q | the node: holds the model, routes everything | no, it *is* the system |
| Leaves | dumb WiFi actuators | individually, yes |
| Phone | listens and speaks | yes |

---

## Status

| Phase | Scope | State |
|---|---|---|
| 1 | Dashboard + phone web client | done |
| 2 | SQLite, TCP leaves, eMMC checkpoints, store-and-forward | done |
| 3 | Sequence model, ONNX + int8, AI Hub, UNO Q deploy | done |
| App | Android (Kotlin/Compose) + Sarvam STT/TTS | **builds; never run on a device** |

**175 checks passing:** `test_phase3.py` 66, `test_phase2.py` 69,
`test_endtoend.py` 33, `test_restart.py` 7, plus `walk_day.py`.

---

## The seam that makes phases stack

`HubState.snapshot()` in `aeon/hubstate.py` is a single JSON state object both
screens render from. A *source* implements `state`, `async run(bcast)`,
`async on_message(msg, bcast)`:

- `aeon/demo_source.py` — Phase 1 scripted house (`run.py --phase 1`)
- `aeon/live_source.py` — the real system (default)

**Phase 2 and 3 landed without a single change to `web/`.** Keep it that way:
to change backend behaviour, change the source, not the UI.

---

## Measured on the Snapdragon X Elite (X1E78100, win-arm64, Python 3.13)

These are the numbers to quote. The x86 Asus figures they replace are in git
history; do not quote those here.

| | X Elite | was (x86) |
|---|---|---|
| Leaf hop (real TCP) | 0.4 – 0.9 ms median across runs | ~1.1 ms |
| Leaf hop (live WebSocket, endtoend) | 0.198 ms; PC hop 0.048 ms | — |
| Model | 2,592 windows, 6,914 params, CV AUC 1.000 | 1,944 / 6,850 |
| Artefact | 28,298 B fp32 → **10,273 B int8** | 10,209 B int8 |
| int8 vs fp32 | decisions identical over 300 windows, max p_on delta 2.0e-4 | same |
| Inference | **~12.7 µs** median idle, ORT CPU | ~41 µs |
| Training | ~1.3 s idle, ~2.2 s inside the suite | ~3.3 s |

Two cautions, both learned the hard way here:

- **Inference timing depends on what else just ran.** The same benchmark reads
  ~12.7 µs idle and ~25 µs when `test_phase3.py` runs it straight after
  cross-validation. Neither is wrong; quote the idle one and say so.
- **The leaf hop is not stable to one decimal.** It moved between 0.404 ms and
  0.896 ms across runs. Quote a range. A sub-millisecond socket round trip
  presented as a single precise figure invites exactly the question you do not
  want on stage.

No QNN on this machine — `onnxruntime` 1.27.0 offers only Azure and CPU
providers. `pip install onnxruntime-qnn` is untried; `NodeRunner` already prefers
QNN when present, so it needs no code change. CPU at ~12.7 µs is entirely
adequate; do not claim NPU.

The design PDF quotes 0.60 ms leaf hop, 0.1–0.4 ms restore, 15.5 µs inference,
2.99 s training. Those were in-process/warm-cache numbers. **Quote measured
values, not the PDF's.**

CV AUC 1.000 reflects training on a synthetic timeline derived deterministically
from stated rules. It says the model learned the rules, not that the task was
hard. Say it that way.

---

## Bugs already found — do not reintroduce

1. **Warm start must be rotated to the target hour.** Shipping a flat 24-step
   window ending at 23:00 and using it to predict 08:00 collapsed every
   prediction to off (`p_on` 0.001 vs 0.997 aligned). The warm day is indexed by
   hour; the node rotates it. `check_alignment()` raises rather than warns.
2. **One unstorable row killed the node↔PC link.** A CHECK-constraint failure
   escaped the PC's connection handler; the socket died and everything spooled
   behind a "healthy" node. Handlers answer with a rejection, never die.
3. **`server.close()` does not unplug anything.** It stops accepting; existing
   sockets survive, so the node kept switching an "unplugged" leaf.
   `LeafDevice.stop()` closes active connections too.
4. **Usage recording must stay off the leaf critical path.** Awaiting it inside
   `actuate()` put a PC round trip inside the measured leaf hop (0.7 → 2 ms) and
   made actuating depend on the PC being reachable.
5. **`n_jobs=-1` is 6× slower on Windows** for the CV (joblib re-imports sklearn
   per worker). Keep `n_jobs=1`.
6. **Off steps record no level.** Writing the model's raw level for an off step
   poisons the lag window silently.
7. **Training and runtime share one occupancy definition** —
   `devices.default_occupancy()`. They disagreed once and predictions collapsed.
8. **Use local midnight, not `time.time() - time.time() % 86400`.** The latter is
   UTC midnight; in IST that shifts every predicted hour by 5:30.
9. **Two-speed loop.** Speaking actuates now but does NOT redeploy the versioned
   policy; that happens on retrain. Collapsing them makes Retrain a no-op.
10. **Windows console is cp1252** — `run.py` reconfigures stdout to UTF-8 or the
    "ÆON" banner kills the process before the server starts.
11. **`await server.wait_closed()` deadlocks while a peer is still connected.**
    Since Python 3.12.1 it waits for every live handler to return, and `_handle`
    only returns when its peer hangs up — so `PCHub.stop()` hung forever on
    3.13 and took `test_phase2.py` with it. Close the live writers *before*
    awaiting, not after. `LeafDevice.stop()` had the same ordering and survived
    only because the leaf tests use short-lived connections. This is bug #3's
    lesson a second time: closing a server does not close its sockets.
12. **`stop()` must drain before it force-closes.** Fixing #11 by killing the
    sockets immediately silently dropped a preference the node had already been
    told was `delivered` — `WifiLink.send()` reports delivered on drain, which
    says nothing about the PC having read it. `PCHub.stop()` now waits a bounded
    moment first. A leaf models pulling the plug and is right to drop everything;
    a PC that loses an acknowledged preference has lost the thing it exists for.
13. **Receiver-side counters lag the sender.** Asserting `pc.received >= 6` on
    the line after a `send()` is a race that passed on x86 by luck. Tests wait on
    conditions — `test_phase2.py` has an `eventually()` helper for exactly this.

---

## Conventions

- No Node/npm. Vanilla HTML/CSS/JS served by FastAPI. One `pip install`.
- The phone is a **web client over LAN** (`/phone`) *and* a native Android app.
- Every hop is HMAC-SHA256 signed; leaves verify before switching.
- `DEVICE_ORDER` is baked into the model's input layout. Appending is safe;
  reordering silently corrupts every prediction, so the node rejects a mismatch.
  Four devices now: AC, fan, light, **robot vacuum**. Adding the vacuum took a
  registry entry, a word list and a seed row — no change to `web/`, and
  `INPUT_DIM` recomputed itself from `len(DEVICE_ORDER)` (105 → 106, params
  6,850 → 6,914). Anything asserting the old literals is a canary and is meant
  to fail; update it deliberately rather than deriving it away.
- **The vacuum is the one device an empty room does not switch off**
  (`off_when_empty=False`). It is deliberately *not* gated to run only when
  empty either: `default_occupancy()` calls 07:00–23:00 occupied, so an
  empty-only vacuum could never honour "clean at 3 PM" — it would accept the
  sentence, learn it, and never act on it. Time preference decides.
- The "off when the room is empty" caption is derived from the registry
  (`devices.occupancy_rule_label()`), so it reads `AC · FAN · LIGHT` rather than
  a hardcoded `ALL` that quietly became false.
- Dashboard is white ground / black ink, monospace. It deliberately shows less
  than the hub knows — in a 5-minute demo an unread number is in the way.
- Tests wait on **conditions**, never on "the next snapshot" — the hub also
  broadcasts on a timer.

---

## Running it

The Python side lives in `simulation/`; `AEON app/` is the Android client and
`docs/` is project documentation. **Everything below runs from `simulation/`.**

```bash
cd simulation
pip install -r requirements.txt
python run.py --reset            # Phase 2/3 real system
python run.py --phase 1          # scripted fallback if something breaks live
```

Dashboard `http://localhost:8800/`, phone `http://<lan-ip>:8800/phone`.

Demo controls on the dashboard: **Retrain** · **Redeploy** (enabled only when the
candidate beats the live model) · **Disable automation**. The old failure-demo
buttons (cut PC link, unsigned, tampered, pause clock) were removed from the UI;
the backend handlers and their tests remain.

`python tools/netcheck.py` answers "why can the phone not reach the hub?".
`python tools/simulate_dataset.py --days 14` gives Retrain something to learn.

```bash
python tests/test_phase3.py
python tests/test_phase2.py
python run.py --reset & python tests/test_endtoend.py
python tests/test_restart.py --managed
python tests/walk_day.py         # deployed model drives leaves through 24 h
```

---

## Not verified — be honest about these

- **Qualcomm AI Hub**: client installed, integration written, no-credentials
  path tested. **No live compile or profile job has run** (needs a token).
- **Android app**: builds (11 MB APK), Sarvam contract verified against the live
  API, but **never run on a phone or emulator**.
- **Arduino UNO Q**: `tools/node_main.py` is written but has not run on real
  hardware.

The UNO Q's Dragonwing is a **QRB2210 — four Cortex-A53 cores, no Hexagon NPU**
like the X Elite has, and AI Hub does not list it as a target. Inference there is
CPU via ONNX Runtime. Fine at 6,850 params, but do not claim NPU on the Arduino.

---

## Sarvam

Verified against the live API (the docs are JS-rendered and 404 on fetch):

| | |
|---|---|
| Auth header | `api-subscription-key` |
| STT | `POST https://api.sarvam.ai/speech-to-text`, multipart field **`file`** (`audio` → 400) |
| STT response | `{request_id, transcript, language_code}` |
| TTS | `POST https://api.sarvam.ai/text-to-speech` |
| TTS body | `{text, target_language_code, speaker, model, pace}` |
| TTS response | `{request_id, audios: ["<base64 wav>"]}` |

Models `saaras:v3` (STT) and `bulbul:v2` / speaker `anushka` (TTS). All strings
live in one companion object in `AEON app/.../net/SarvamClient.kt`.

**The key lives in `AEON app/local.properties` (gitignored). Never commit it.**
It was pasted in plain chat during development, so rotate it after the event.
