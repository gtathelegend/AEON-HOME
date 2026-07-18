# Qualcomm AI Hub — running the optimisation step

AI Hub compiles the exported ONNX for a chosen Snapdragon target and profiles it
on that silicon in Qualcomm's device farm, so latency and memory are *measured on
hardware* rather than asserted.

It is **strictly optional**. Training, export, int8 quantisation and deployment
all work without it. `aeon/aihub.py::status()` reports whether it is usable and
`optimize()` returns a reason instead of raising, because a demo must not die
because a cloud service was slow.

---

## It lives in its own virtualenv, on purpose

`qai-hub` pins **protobuf back to 6.x**. The runtime stack here is on **7.x**, and
`onnx` sits on top of protobuf's C extension. Installing `qai-hub` into `.venv`
downgrades protobuf underneath a working ONNX export path — which is the one
thing in this project that must not break.

So AI Hub gets `.venv-aihub` and the demo stack is never touched:

```powershell
python -m venv .venv-aihub
.venv-aihub\Scripts\python.exe -m pip install -r requirements.txt qai-hub
```

Verified on the X Elite (win-arm64): `qai-hub` 0.52.0 installs from wheels, no
source build. `.venv*/` is gitignored, so neither venv can be committed.

This split is safe because AI Hub is an **offline build step**. It reads an
exported `.onnx` file and returns numbers. Nothing at runtime imports it.

| | `.venv` | `.venv-aihub` |
|---|---|---|
| protobuf | 7.35.1 | 6.31.1 |
| runs | `run.py`, all tests, the demo | `tools/aihub_optimize.py` only |

---

## Running it

You need a Qualcomm account and an API token — free, but it is an account
signup, so it cannot be scripted.

```powershell
# 1. Token from https://aihub.qualcomm.com
.venv-aihub\Scripts\qai-hub.exe configure --api_token <token>

# 2. What can this account actually target?
.venv-aihub\Scripts\python.exe tools\aihub_optimize.py --devices

# 3. Compile + profile
.venv-aihub\Scripts\python.exe tools\aihub_optimize.py --device "Snapdragon X Elite CRD"
```

Run it once before quoting any AI Hub number.

---

## Verified state

Everything **except the cloud call** is exercised and working:

```
  AI Hub client : installed v0.52.0
  credentials   : NOT configured
  -> no API token: get one at https://aihub.qualcomm.com and run `qai-hub configure --api_token <token>`
  training on   : 6 active preferences
  model         : 2,592 windows, 6,914 params, cv auc 1.000
  artefact      : fp32 28,298 B -> int8 10,273 B
  written       : build/aeon_ts_int8.onnx (sha256 5328aeafe1be4de3)
  local (CPU): median 12.4 us, p95 15.7 us

  Skipping AI Hub: no credentials. The int8 ONNX above is a complete,
  deployable artefact -- AI Hub adds measured on-device numbers, not
  a dependency.
```

So the train → export → quantise → benchmark → graceful-degrade path is proven.
**No live compile or profile job has ever run.** That needs the token, and until
one has run, do not quote an AI Hub latency, memory figure or compute unit.

---

## What must not be claimed

The Arduino UNO Q's Dragonwing side is a **QRB2210** — four Cortex-A53 cores. It
does **not** carry the Hexagon NPU an X Elite or an 8-series part does, and AI Hub
does not list it as a target. Inference on the UNO Q is **CPU inference through
ONNX Runtime**, which is entirely adequate at 6,914 parameters and ~12 µs — but
it is CPU.

AI Hub profiling here answers *"how does this artefact behave on Snapdragon
hardware"*, which is real and checkable. It does not answer *"the Arduino runs it
on an NPU"*, which would not be true.

The AI PC has no QNN either: `onnxruntime` 1.27.0 on this machine offers only
Azure and CPU providers. `pip install onnxruntime-qnn` is untried; `NodeRunner`
already prefers `QNNExecutionProvider` when present, so it needs no code change.
