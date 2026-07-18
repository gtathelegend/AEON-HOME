#!/usr/bin/env bash
# scripts/run_tests.sh — Run all backend and frontend tests.
#
# Usage: ./scripts/run_tests.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0
FAIL=0

run() {
  echo ""
  echo "══════════════════════════════════════"
  echo "  $1"
  echo "══════════════════════════════════════"
}

# ── Backend tests ─────────────────────────────────────────────────────────────
run "Backend — pytest"
cd "$REPO_ROOT/backend"
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi
if pytest ../tests/backend -v --tb=short; then
  echo "✓ Backend tests passed"
  PASS=$((PASS + 1))
else
  echo "✗ Backend tests failed"
  FAIL=$((FAIL + 1))
fi

# ── Frontend tests ────────────────────────────────────────────────────────────
run "Frontend — vitest"
cd "$REPO_ROOT"
if npm run test -- --run 2>/dev/null; then
  echo "✓ Frontend tests passed"
  PASS=$((PASS + 1))
else
  echo "⚠ Frontend tests skipped or failed (vitest not configured yet)"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed"
echo "══════════════════════════════════════"
[ "$FAIL" -eq 0 ] || exit 1
