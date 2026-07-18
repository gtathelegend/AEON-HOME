---
name: aeon-repo-and-migration
description: ÆON Home lives on branch AEON-V0 of gtathelegend/AEON-Home-Internal; how to resume on the X Elite AI PC
metadata:
  type: project
---

The codebase is on branch **`AEON-V0`** of
<https://github.com/gtathelegend/AEON-Home-Internal> (private; user has WRITE
as `Akshatkasera`). Pushed 2026-07-18 from the Asus dev laptop for the move to
the Lenovo Snapdragon X Elite AI PC, which is the demo machine.

**Resume flow on a new machine:** clone → `pip install -r requirements.txt` →
`python tools/preflight.py` → `python tools/restore_memory.py --write` → start
Claude Code from the repo root.

`CLAUDE.md` at the repo root is the real handoff: architecture, phase status,
measured numbers, and the ten bugs already found and fixed. It loads
automatically and is path-independent. `docs/HANDOFF.md` is the migration
runbook.

**Why `restore_memory.py` exists:** Claude Code names a project's memory folder
after the project's absolute path (`C:\Users\aksha\Downloads\AEON home code` →
`C--Users-aksha-Downloads-AEON-home-code`). Clone to any other path and the old
memory silently is not found — no error. The script recomputes the folder for
wherever the repo now lives.

**Never committed:** `AEON app/local.properties` holds the Sarvam key and is
gitignored; it must move out of band (USB / password manager). `data/` is
gitignored too — it regenerates via `python run.py --reset`, and the x86 build
output is wrong for ARM64 anyway.

**Why:** the demo runs on the X Elite, and a naive folder copy would carry stale
x86 build artefacts, lose the development context, and risk publishing an API key.

**How to apply:** the submission repo must be **PUBLIC** — AEON-Home-Internal is
private, so a separate public repo is still needed before the 2026-07-19 13:00
IST deadline. See [[aeon-hackathon-deadline]] and [[aeon-phase-plan]].
