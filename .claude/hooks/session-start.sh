#!/usr/bin/env bash
# session-start.sh — SessionStart hook: print a few facts every session needs.
# Stdout is injected as context at the top of the session.

source "$( dirname "${BASH_SOURCE[0]}" )/_repo.sh"

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
echo "SESSION CONTEXT: on branch '$branch'. CLAUDE.md is canonical; read it before changing code."

if [ -f "$REPO/config.py" ]; then
  echo "config.py is present (real settings; never print or commit it)."
else
  echo "No config.py: tests load config.example.py instead. Add any new config.X setting to config.example.py."
fi

echo "Check before finishing: ./scripts/check.sh (ruff + guardrails + pytest)."
