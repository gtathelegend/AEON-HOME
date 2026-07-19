#!/usr/bin/env python3
"""Restore Claude Code's project memory on a new machine.

    python tools/restore_memory.py            # show what would happen
    python tools/restore_memory.py --write

Claude Code keys a project's memory directory to the project's ABSOLUTE PATH:

    ~/.claude/projects/<path with non-alphanumerics replaced by dashes>/memory/

So `C:\\Users\\aksha\\Downloads\\AEON home code` becomes
`C--Users-aksha-Downloads-AEON-home-code`. Copy the repo to a different path on
a new laptop and the old memory silently does not load -- no error, it is simply
not found. This script computes the correct folder for wherever the repo now
lives and copies `docs/memory/` into it.

Most of the context lives in CLAUDE.md at the repo root, which Claude Code loads
regardless of path. This restores the rest.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent

# docs/ lives at the repo root, above simulation/. Walk up to find it rather
# than hardcoding a number of parents that changes if the tree is rearranged.
def _repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists() or (candidate / "docs").is_dir():
            return candidate
    return start


REPO = _repo_root(ROOT)
SOURCE = REPO / "docs" / "memory"


def slug_for(path: Path) -> str:
    """Mirror Claude Code's project-directory naming."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def main() -> int:
    ap = argparse.ArgumentParser(description="Restore project memory")
    ap.add_argument("--write", action="store_true", help="actually copy")
    # Keyed on the REPO root: that is the directory Claude Code is started from,
    # and the slug is derived from it. simulation/ would compute a folder that
    # exists but is never loaded.
    ap.add_argument("--project", default=str(REPO), help="project path to key on")
    args = ap.parse_args()

    project = Path(args.project).resolve()
    target = Path.home() / ".claude" / "projects" / slug_for(project) / "memory"

    print()
    print(f"  project   {project}")
    print(f"  slug      {slug_for(project)}")
    print(f"  memory ->  {target}")
    print()

    if not SOURCE.exists():
        print(f"  nothing to restore: {SOURCE} does not exist\n")
        return 1

    files = sorted(p for p in SOURCE.glob("*.md"))
    if not files:
        print(f"  nothing to restore: no .md files in {SOURCE}\n")
        return 1

    for path in files:
        exists = (target / path.name).exists()
        print(f"    {path.name:34} {'OVERWRITE' if exists else 'new'}")

    if not args.write:
        print("\n  dry run. Re-run with --write to copy.\n")
        return 0

    target.mkdir(parents=True, exist_ok=True)
    for path in files:
        shutil.copy2(path, target / path.name)

    print(f"\n  copied {len(files)} file(s). Start Claude Code from {project}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
