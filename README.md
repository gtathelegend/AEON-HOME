# ÆON Home

**Adaptive smart-device control from learned time preferences. All on the edge.**

State a preference once, in plain language — *"Set the AC to 25 degrees at 9 PM."*
The command reaches the appliance in under a millisecond and the model by the next
retrain. Nothing leaves the house in the control loop.

Built for the Snapdragon Multiverse Hackathon, Noida — July 18–19, 2026.

---

## The idea

A smart home today is either dumb or exhausting. A plain appliance repeats itself
whether you are home or not.

ÆON Home learns your preferences from what you say. Each sentence goes to the
central node, which switches the appliance **immediately** and forwards the same
command to the AI PC. The PC retrains and pushes the updated model back.

| Device | Learns | Driven by |
|---|---|---|
| AC | setpoint, 16–30 °C | what you said, and when |
| Fan | speed, 0–100 % | ambient temperature |
| Light | colour, 2200–6500 K | time of day |
| Robot vacuum | suction, 0–100 % | the hour you told it to clean |

The AC, fan and light also turn off when the room is empty. The vacuum is
deliberately exempt: an empty room is a *good* time to clean, not a reason to
stop. It is not restricted to an empty room either — occupancy is marked
07:00–23:00, so a vacuum gated to "only when empty" could never honour *"clean
at 3 PM"*. It would accept the sentence, learn it, and then silently never act
on it. The vacuum runs on the time preference you state, and occupancy stays out
of its way.

### The division of labour is the design

| Role | | Can it be switched off? |
|---|---|---|
| **AI PC** | learns — needs a real machine | yes, the house keeps running |
| **Arduino UNO Q** | the central node — holds every model, routes every command | no, it *is* the system |
| **Leaf devices** | dumb WiFi actuators — relay, IR, driver | individually, yes |
| **Phone** | listens and speaks | yes |

Your phone talks to the central node, not to the PC. Your laptop can be asleep;
the house still responds.

### The fan-out rule

```
Phone ──► CENTRAL NODE ──1──► targeted leaf   (the appliance responds NOW)
                        └─2──► PC              (the preference becomes training data)
```

Neither failure is allowed to break the other:

| Failure | What happens |
|---|---|
| PC offline | leaf still actuates; the record spools and replays on reconnect |
| Leaf offline | the command still reaches the PC, so the preference is still learned |

Every message on every hop is HMAC-SHA256 signed. A leaf switches a real
appliance, so it verifies before acting.

---

## Build phases

| Phase | Scope | Status |
|---|---|---|
| **1** | Dashboard + phone client, live over WebSocket, driven by a scripted house | ✅ done |
| **2** | Real backend — SQLite, central node, TCP leaf devices, eMMC checkpoints, store-and-forward | ✅ done |
| **3** | Sequence model, ONNX + int8, AI Hub, deployment to the Arduino UNO Q | ✅ **done** |
| **App** | Android client (Kotlin/Compose) with Sarvam STT/TTS — see [`AEON app/`](AEON%20app/README.md) | ✅ builds |

Phases stack on one seam — `HubState.snapshot()`. The dashboard never learns
whether its data came from the scripted house or the real node, so Phase 2
landed underneath a finished UI **without a single change to `web/`**. The robot
vacuum was added the same way: a registry entry and a word list, no UI work at
all — the fourth tile, its learned schedule and its leaf all came through the
same snapshot.

Run either: `python run.py` for Phase 2, `python run.py --phase 1` for the
scripted house.

### What is real as of Phase 2

Everything crosses a socket. The four leaves are real TCP servers that verify
HMAC-SHA256 before switching, and reject unsigned or tampered commands on the
wire. Preferences persist in SQLite with full supersession history. The node
keeps durable eMMC checkpoints (magic + CRC32, durable-replace, 3 generations)
and restores them after a hard kill. Unreachable-PC records spool to disk and
replay on reconnect. Policy deploys carry a manifest and are rejected on hash
mismatch or `device_order` mismatch.

In the demo the leaves are loopback ports; on the table they are ESP32s on the
WiFi speaking exactly this protocol. Nothing about the node changes.

### What is still simulated

The **ambient sensor feed** — `aeon/sim.py` generates a plausible day because
there is no DHT22 on the bench. Replace `read_ambient()` in
[`tools/node_main.py`](tools/node_main.py) to wire a real sensor.

Everything else is real, including the model.

---

## The model

Trained on the AI PC, deployed to and executed on the node.

```
input (106) ──► Dense(32) + tanh ──► Dense(1) + sigmoid ──► p_on
            └─► Dense(32) + tanh ──► Dense(1)           ──► level
```

    window   24 steps x 4 channels                  =  96
    context  hour sin/cos, dow sin/cos, weekend, ambient z   =   6
    device one-hot                                          =   4
                                                    input   = 106

**6,914 parameters.** Two heads, because "should it be on?" and "at what
setting?" are different questions. One model serves all four appliances — each
window carries a device one-hot, so shared structure (an empty room means off,
the daily rhythm) is learned once rather than four times, and there is one
deploy target and one rollback target.

Adding the vacuum is what that buys you: it was appended to `DEVICE_ORDER`, given
a registry entry and a word list, and it arrived as a fourth tile with its own
learned schedule. Appending is safe because it shifts no existing one-hot index;
reordering would silently corrupt every prediction, which is why the node rejects
a model whose `device_order` disagrees with its own.

A stated preference is expanded into a coherent 28-day timeline rather than
stored as one row. **One row per timestep, never duplicated** — repeating a
preference to weight it fills the 24-step lag window with N copies of the same
hour, and the model then trains on histories that cannot physically occur.

### Measured on the Snapdragon X Elite (X1E78100, win-arm64)

| | |
|---|---|
| Pooled training windows | 2,592 |
| Parameters | 6,914 |
| Cross-validated AUC | 1.000 |
| Training wall time | ~1.3 s idle, ~2.2 s in the full suite |
| Artefact | 28,298 B fp32 → **10,273 B int8** |
| int8 vs fp32 | on/off decisions **identical** over 300 windows; max p_on delta 2.0e-4 |
| Inference | **~12.7 µs** median, ONNX Runtime CPU |
| Level MAE | AC 0.27 °C · fan 0.647 % · light 33.4 K · vacuum 1.045 % |

Inference is timed on an otherwise idle machine. The same benchmark run
immediately after cross-validation inside `test_phase3.py` reads ~25 µs, because
it is competing with the training that just finished — worth knowing before
quoting whichever number the terminal happened to show.

CV AUC 1.000 reflects training on a synthetic timeline derived
deterministically from stated rules — it says the model learned the rules, not
that the task was hard. Say it that way.

### Guardrails — a bad model never reaches the node

1. ≥200 windows, and both on and off present.
2. Judged on **cross-validated** AUC ≥ 0.60, never training AUC — an overfit
   model wins on its own training data every time.
3. A candidate must beat the incumbent, or it is rejected and the deployed
   model stays live.
4. The node verifies sha256, `device_order`, window and input_dim before
   loading. A truncated transfer can never become a live policy.
5. A **cold buffer never acts**: confidence is capped below the act threshold
   until a real 24-step window exists.

### Deploying with the context the model expects

An autoregressive model reads its own recent output, so a freshly deployed node
with an all-off window is self-fulfilling: it predicts off, records off, and
never bootstraps into the pattern.

So the model ships with the last trained day **indexed by hour**, and the node
rotates it to end at the hour before now. Indexing matters: the first build
shipped a flat 24-step window ending at 23:00, the node used it to predict
08:00, and every prediction collapsed to off — `p_on` 0.001 where the same model
on an aligned window gives 0.997. `check_alignment()` raises rather than warns,
because that failure is invisible from the outputs.

---

## Qualcomm AI Hub

```bash
pip install qai-hub
qai-hub configure --api_token <token>        # https://aihub.qualcomm.com

python tools/aihub_optimize.py --devices     # what can this account target?
python tools/aihub_optimize.py --device "Snapdragon X Elite CRD"
```

**What AI Hub does here:** compiles the exported ONNX for a chosen Snapdragon
target and profiles it on that silicon in Qualcomm's device farm, so latency and
memory are *measured on hardware* rather than asserted.

**What it does not do, and should not be claimed:** the Arduino UNO Q's
Dragonwing side is a QRB2210 — four Cortex-A53 cores, no Hexagon NPU of the kind
an X Elite or 8-series part carries — and AI Hub does not list it as a target.
Inference on the UNO Q is **CPU inference through ONNX Runtime**. That is
entirely adequate at 6,850 parameters and ~41 µs, but it is CPU, and the demo
should say so.

AI Hub is **strictly optional**. Training, export, int8 quantisation and
deployment all work without it; `aeon/aihub.py::status()` reports whether it is
usable and `optimize()` returns a reason instead of raising. A hackathon demo
must not die because a cloud service was slow.

> ⚠️ **Not verified end to end.** The integration is written and the
> no-credentials path is tested, but no live compile or profile job has been
> run — that needs a Qualcomm account token. Run `tools/aihub_optimize.py`
> once you have one, before quoting any AI Hub number.

---

## Deploying to the Arduino UNO Q

The same `CentralNode` that runs in the demo runs standalone on the UNO Q's
Dragonwing (Debian) side:

```bash
# on the UNO Q
sudo apt install python3-pip
pip3 install onnxruntime numpy

python3 tools/node_main.py \
    --pc 192.168.1.42:9800 \
    --leaf ac.living=192.168.1.51:9001 \
    --leaf fan.bedroom=192.168.1.52:9001 \
    --leaf light.living=192.168.1.53:9001 \
    --data /var/lib/aeon
```

The node holds the model, runs every inference and routes every command. It does
not switch loads — the leaves do. It does not need the PC: close the laptop and
it keeps running, spooling what it cannot deliver to `/var/lib/aeon/spool.jsonl`
and replaying on reconnect.

Restore and reconnect are reported separately, because they are different: eMMC
restore is sub-millisecond to tens of milliseconds, WiFi association takes
seconds. The node resumes **controlling** instantly and resumes **learning**
when the network returns.

### The two-speed loop

Speaking a preference actuates the appliance **now** and records it on the PC.
It deliberately does **not** redeploy the versioned policy. That happens on
retrain. One correction should feel instant, but one correction should not
rewrite a weekly rhythm — and collapsing the two also makes the Retrain button
a no-op by the time anyone presses it.

Retraining an unchanged policy reports "policy unchanged" and does not mint a
version, so the deployment log keeps answering *when did behaviour actually
change?*

---

## Repository layout

```
simulation/     the hub: backend, dashboard, model, tests, tools  (Python)
AEON app/       the Android client                                (Kotlin)
docs/           AI Hub notes, migration runbook, project memory
```

Everything below runs from `simulation/`.

## Setup from scratch

Requires Python 3.11 or newer. No Node, no npm, no build step.

```bash
git clone https://github.com/gtathelegend/AEON-HOME.git
cd AEON-HOME/simulation
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Run

```bash
python run.py
```

```
  ÆON HOME · HUB
  ──────────────────────────────────────────────
  dashboard   http://localhost:8800/
  phone       http://192.168.1.42:8800/phone
  ──────────────────────────────────────────────
  same WiFi, no cloud, no pairing
```

Open the **dashboard** URL on the AI PC and the **phone** URL on your phone.
Both must be on the same WiFi. Nothing else is required — no account, no pairing,
no cloud service.

### Using it

On the phone, either hold the mic and say a preference, or type one:

- `set the AC to 25 degrees at 9 PM`
- `run the fan at full speed at 3 PM`
- `night light at 11 PM`
- `vacuum the house at 3 PM`
- `deep clean at 11 AM on weekdays`
- `AC ko 23 degree pe chalao 9 baje` — code-mixed Hindi/English works
- `safai karo 9 baje` — so does the vacuum

The dashboard shows the command hitting two destinations, with the measured
latency of each hop.

The dashboard's own buttons drive the failure demos:

| Button | What it shows |
|---|---|
| **Retrain & deploy** | one training run across all devices → int8 artefact → hash-verified deploy |
| **Cut PC link** | leaf still actuates, record spools, flushes on reconnect |
| **Unsigned command** | rejected — bad signature, device unchanged |
| **Tampered command** | rejected — signed, then modified after signing |
| **Pause clock** | freeze the demo clock (one demo hour ≈ 3.75 s) |

### On what the dashboard deliberately does not show

The hub knows more than the screen reports — pooled window count, parameter
count, per-device MAE, checkpoint sequence, wall-clock training time, packet
counts. All of it is in `HubState`, and none of it is on the dashboard.

In a five-minute judged demo a number nobody reads is a number in the way. The
screen shows the four appliances, the fan-out proof with its measured latency,
and the model version. The rest stays one `snapshot()` call away for anyone who
asks.

## Tests

```bash
# 66 model checks — training, ONNX, int8 parity, guardrails, node inference
python tests/test_phase3.py

# 69 component checks — checkpoints, parsing, transport, leaves, node
python tests/test_phase2.py

# 33 checks against a live hub (start it with --reset first)
python run.py --reset
python tests/test_endtoend.py

# 7 checks that the house survives a hard kill
python tests/test_restart.py --managed

# watch the deployed model drive the leaves through 24 hours
python tests/walk_day.py

# what actually persisted, and what the last retrain deployed
python tests/inspect_db.py
python tests/inspect_policy.py
```

175 checks in total.

`test_phase2.py` drives the real objects directly, so a failure points at the
component that broke rather than at a timing race: checkpoint CRC and generation
fallback, intent parsing, supersession, spool-and-replay, leaf signature
rejection, hash- and `device_order`-rejected deploys, and node restart.

`test_endtoend.py` drives the real WebSocket. Every assertion waits on a
*condition* rather than on "the next snapshot" — the hub also broadcasts on a
timer, and waiting on snapshot counts makes the suite flaky in a way that looks
like a product bug. It needs a hub started with `--reset`; against a stale
database the policy is already current and the retrain check fails for reasons
unrelated to the code.

### Measured on the Snapdragon X Elite

| | |
|---|---|
| Leaf hop (central → leaf → ack, real TCP) | **0.4 – 0.9 ms** median across runs |
| Leaf hop with the PC unplugged | comparable — the leaf path does not depend on the PC |
| Leaf hop over the live WebSocket (`test_endtoend`) | **0.198 ms**, PC hop 0.048 ms |

The design doc quotes 0.60 ms for the leaf hop and 0.1–0.4 ms for restore. Those
were in-process and warm-cache numbers; these cross a real socket. Quote the
measured ones — and quote a range, because the leaf hop moved between 0.404 ms
and 0.896 ms across runs on this machine. A single decimal place of a
sub-millisecond socket round trip is not a stable quantity, and presenting one
as though it were invites the question you least want on stage.

---

## Layout

Paths below are relative to `simulation/`.

| File | Role |
|---|---|
| `aeon/devices.py` | device registry — level ranges, normalisation, occupancy |
| `aeon/protocol.py` | HMAC-SHA256 signing and the message table |
| `aeon/hubstate.py` | the single state object every screen renders from |
| `aeon/server.py` | WebSocket hub + static serving |
| `aeon/commands.py` | speech → structured preference, supersession, compiled schedule |
| `aeon/db.py` | SQLite — telemetry, usage, commands, deployments, models |
| `aeon/checkpoint.py` | durable eMMC checkpoints — magic + CRC32, 3 generations |
| `aeon/wifi_link.py` | store-and-forward node → PC |
| `aeon/leaf.py` | a dumb WiFi actuator that verifies before it switches |
| `aeon/central.py` | the node — holds the policy, routes every command |
| `aeon/pc.py` | the AI PC — SQLite, TCP server, compiles the policy |
| `aeon/sequence.py` | the 24-step lag window, features, alignment |
| `aeon/tsmodel.py` | synthesis, training, ONNX export, int8, guardrails |
| `aeon/runner.py` | ONNX Runtime inference on the node |
| `aeon/aihub.py` | optional Qualcomm AI Hub compile + profile |
| `aeon/live_source.py` | Phase 2/3 wiring, adapted to `HubState` |
| `aeon/demo_source.py` | Phase 1 scripted house |
| `aeon/sim.py` | the ambient curve — the one genuinely fake part |
| `tools/node_main.py` | run the node standalone on the Arduino UNO Q |
| `tools/aihub_optimize.py` | compile and profile on Snapdragon silicon |
| `web/dashboard.*` | PC dashboard — full control view |
| `web/phone.*` | phone client — personal view, mic + tiles |
| `tests/` | component, end-to-end and restart suites |

## Notes

- **Privacy.** Usage history stays on the AI PC. The egress ledger on the
  dashboard reports cloud bytes, and it reads zero. Phase 3 adds Sarvam
  STT/TTS for speech; if that runs as a cloud API the honest claim becomes
  "usage history never leaves your home; the voice channel is an opt-in cloud
  call." Phase 1 uses the browser's own speech API.
- **On the word "WebSocket".** The phone channel is a real RFC-6455 WebSocket
  here. The node↔PC link in Phase 2 is newline-delimited signed JSON over TCP —
  identical payloads, one less dependency. Worth saying plainly rather than
  claiming a WebSocket that isn't one.
- **`DEVICE_ORDER` is fixed** because it is baked into the deployed model's input
  layout. Appending a device is safe; reordering silently corrupts every
  prediction, so the node rejects a model whose `device_order` disagrees.

## Team

<!-- SUBMISSION REQUIREMENT: names and emails of every eligible team member.
     Fill this in before submitting — the rules ask for it explicitly. -->

| Name | Email |
|---|---|
| _your name_ | kaseraakshat07@gmail.com |
| | |

## License

MIT — see [LICENSE](LICENSE).
