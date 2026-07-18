# Moving to the Snapdragon X Elite AI PC

Runbook for shifting development and the demo from the Asus dev laptop to the
Lenovo Snapdragon X Elite. Do this **while you still have good network**, not at
the venue.

The whole repo is ~0.4 MB of actual source. The other ~58 MB is build output and
generated data that must **not** move — it is x86 build output, and regenerating
it on the target is both faster and correct.

---

## 1. On the Asus — push to GitHub

You need a public repo for submission anyway, so this is the transfer *and* a
deliverable.

```bash
cd "C:\Users\aksha\Downloads\AEON home code"

git init -b main
git add -A
git status                       # confirm no local.properties, no data/, no build/
git commit -m "AEON Home: phases 1-3, Android app, tooling"

gh repo create aeon-home --public --source=. --push
# or: git remote add origin https://github.com/<you>/aeon-home.git && git push -u origin main
```

**Before pushing, confirm the key is not in the diff:**

```bash
git ls-files | Select-String "local.properties"     # must return nothing
git grep -i "sk_ppf" -- . 2>$null                   # must return nothing
```

`.gitignore` already excludes `local.properties`, `data/`, `build/`, `*.onnx`,
`*.ckpt` and `hub.out/err`.

---

## 2. Carry the secret separately

The Sarvam key is deliberately **not** in the repo. Move it by hand:

- Source: `AEON app/local.properties` → the `sarvam.key=` line
- Destination: same file on the new laptop, created from
  `AEON app/local.properties.example`

USB stick, password manager, or type it. **Not** email, chat or the repo.

Rotate the key at <https://dashboard.sarvam.ai> after the hackathon — it was
pasted in plain chat during development.

---

## 3. On the Lenovo — clone and preflight

```bash
git clone https://github.com/<you>/aeon-home.git
cd aeon-home

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
python tools/preflight.py
```

`preflight.py` is the important step. It checks Python version, every import,
ONNX Runtime providers, LAN address, port 8800, and then actually trains,
quantises and runs the model end to end. **ARM64 Windows is where dependencies
break** — a package with no `win_arm64` wheel makes pip build from source, which
either takes twenty minutes or fails. Find that out now.

If something has no ARM64 wheel, try in this order:

1. `pip install --upgrade pip` first — wheel availability improves with pip version.
2. `pip install --only-binary=:all: <package>` to confirm a wheel truly exists.
3. Newer version of that package (ARM64 wheels arrived late for numpy/scipy).
4. Worst case, `python run.py --phase 1` needs **only** fastapi/uvicorn/websockets
   and gives you a working dashboard demo with no ML stack at all.

### Try the NPU while you are there

```bash
pip install onnxruntime-qnn
python tools/preflight.py          # look for QNNExecutionProvider
```

`NodeRunner` already prefers `QNNExecutionProvider` when present, so this needs
no code change. If it appears, inference on the AI PC moves to the Hexagon NPU
and you have a genuine Snapdragon-acceleration claim for the judges. If it does
not, CPU at ~41 µs is entirely adequate — do not force it.

---

## 4. Restore the development context

`CLAUDE.md` at the repo root loads automatically and holds the architecture,
current status, measured numbers, and the ten bugs already found. That is the
bulk of it and it travels with the clone.

For the rest:

```bash
python tools/restore_memory.py            # dry run — shows the computed path
python tools/restore_memory.py --write
```

Claude Code names a project's memory folder after its **absolute path**
(`C:\Users\aksha\Downloads\AEON home code` → `C--Users-aksha-Downloads-AEON-home-code`).
Clone to a different path and the old memory silently does not load. This script
computes the right folder for wherever the repo now lives.

Then start Claude Code **from the repo root** so it picks up `CLAUDE.md`. Log in
with your own account there; nothing about the login carries over.

---

## 5. Verify on the new machine

```bash
python tests/test_phase3.py
python tests/test_phase2.py

python run.py --reset               # terminal 1
python tests/test_endtoend.py       # terminal 2
python tests/walk_day.py

python tests/test_restart.py --managed
```

Expect **175 checks**. Then **re-measure** — the numbers in `CLAUDE.md` and the
README are from x86 and are not what you should quote on stage:

```bash
python tests/test_phase2.py | Select-String "leaf hop median"
python tests/test_phase3.py | Select-String "median"
```

---

## 6. Demo-day setup on the Lenovo

- **Firewall:** the first `python run.py` triggers a Windows Firewall prompt.
  **Allow on private networks** or the phone cannot reach the dashboard. If you
  miss the prompt: Windows Security → Firewall → Allow an app → Python.
- **LAN:** `run.py` prints the phone URL. Phone and laptop on the same WiFi.
  Venue WiFi often isolates clients — a **phone hotspot with the laptop joined to
  it** is the reliable fallback.
- **Android app:** open `AEON app/` in Android Studio, restore
  `local.properties`, `./gradlew installDebug`. First build on ARM64 downloads a
  fresh Gradle distribution — do this before the venue.
- **Arduino UNO Q:** `tools/node_main.py` on the Dragonwing side, with
  `--leaf device=host:port` for each leaf. Needs `pip3 install onnxruntime numpy`.
  **Untested on real hardware — budget time.**
- **Always have `python run.py --phase 1` ready.** No sockets, no database, no ML
  stack; if anything is broken five minutes before you present, it still demos
  the fan-out story.

---

## What not to move

`data/`, `build/`, `AEON app/build/`, `AEON app/.gradle/`, `.idea/`,
`__pycache__/`, `.venv/`, `hub.out`, `hub.err`.

All regenerate, and the x86 build output is wrong for ARM64. `run.py --reset`
rebuilds `data/` from scratch, which is what you want before a demo anyway.

---

## If GitHub is not an option

```powershell
# on the Asus
cd "C:\Users\aksha\Downloads"
Compress-Archive -Path "AEON home code\*" -DestinationPath aeon.zip -Force
```

Then delete `data`, `build`, `.gradle`, `.venv`, `__pycache__` from the archive,
and copy `AEON app/local.properties` separately. But push to GitHub if you can —
the submission requires a public repo regardless.
