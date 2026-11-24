#!/usr/bin/env bash
# check.sh — the one command to run before committing or opening a PR.
# Mirrors CI (.github/workflows/test.yml): ruff gate, guardrails, pytest, and the
# web app (web/) when Node.js is installed.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== ruff =="
if command -v ruff >/dev/null 2>&1; then ruff check .; else poetry run ruff check .; fi

echo "== guardrails =="
python3 scripts/guardrails.py --all

echo "== pytest =="
poetry run python -m pytest -q tests "$@"

if command -v npm >/dev/null 2>&1; then
  echo "== web =="
  (cd web && { [[ -d node_modules ]] || npm ci --no-audit --no-fund; } && npm run gen:api && npm run typecheck && npm test && npm run build)
else
  echo "== web: skipped (Node.js isn't installed) =="
fi
