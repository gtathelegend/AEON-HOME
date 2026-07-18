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

## Measured on the dev machine (x86 Asus)

Re-measure on the X Elite; do not quote these there.

| | |
|---|---|
| Leaf hop (real TCP) | ~1.1 ms median; ~1.3 ms with the PC unplugged |
| Checkpoint restore | ~12 ms cold, <1 ms warm |
| Model | 1,944 windows, 6,850 params, CV AUC 1.000 |
| Artefact | 28,042 B fp32 → **10,209 B int8** |
| int8 vs fp32 | decisions identical over 300 windows |
| Inference | ~41 µs median, ORT CPU |
| Training | ~3.3 s warm (~8 s extra on the first run) |

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

---

## Conventions

- No Node/npm. Vanilla HTML/CSS/JS served by FastAPI. One `pip install`.
- The phone is a **web client over LAN** (`/phone`) *and* a native Android app.
- Every hop is HMAC-SHA256 signed; leaves verify before switching.
- `DEVICE_ORDER` is baked into the model's input layout. Appending is safe;
  reordering silently corrupts every prediction, so the node rejects a mismatch.
- Dashboard is white ground / black ink, monospace. It deliberately shows less
  than the hub knows — in a 5-minute demo an unread number is in the way.
- Tests wait on **conditions**, never on "the next snapshot" — the hub also
  broadcasts on a timer.

---

## Running it

```bash
pip install -r requirements.txt
python run.py --reset            # Phase 2/3 real system
python run.py --phase 1          # scripted fallback if something breaks live
```

Dashboard `http://localhost:8800/`, phone `http://<lan-ip>:8800/phone`.

Demo controls on the dashboard: Retrain & deploy · Cut PC link · Unsigned
command · Tampered command · Pause clock.

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
