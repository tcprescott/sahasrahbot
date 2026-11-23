#!/usr/bin/env bash
# install-deps.sh — SessionStart hook: install Python dependencies so tests,
# ruff and imports work from the first turn of a cloud session.
#
# Web-only: skipped on local machines, where the venv is managed by hand.
# Never edits pyproject.toml or poetry.lock.
set -uo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

source "$( dirname "${BASH_SOURCE[0]}" )/_repo.sh"

# Production runs Python 3.11. Newer interpreters break the pinned discord.py
# (3.13 removed `audioop`), so prefer 3.11 when the container has it.
if command -v python3.11 >/dev/null 2>&1; then
  poetry env use python3.11 >/dev/null 2>&1 || true
fi

# racetime-bot is pinned as a GitHub archive URL, which the cloud egress proxy
# can refuse. Install everything Poetry can, then fall back to a git install of
# the same commit for racetime-bot if it is still missing.
poetry install --no-root --no-interaction --no-ansi >/tmp/poetry-install.log 2>&1 || true

if ! poetry run python -c "import racetime_bot" >/dev/null 2>&1; then
  ref=$(grep -o 'racetime-bot/archive/[0-9a-f]*' pyproject.toml | head -1 | sed 's|.*/||')
  if [ -n "$ref" ]; then
    poetry run python -m pip install -q "racetime-bot @ git+https://github.com/tcprescott/racetime-bot@${ref}" \
      >>/tmp/poetry-install.log 2>&1 || true
  fi
fi

# Test tooling. pytest is not (yet) in the Poetry dev group; install it into the
# venv without touching the dependency files.
if ! poetry run python -c "import pytest" >/dev/null 2>&1; then
  poetry run python -m pip install -q --only-binary=:all: pytest >>/tmp/poetry-install.log 2>&1 || true
fi
command -v ruff >/dev/null 2>&1 || pipx install ruff >/dev/null 2>&1 || true

if poetry run python -c "import discord, racetime_bot, pytest" >/dev/null 2>&1; then
  echo "Dependencies installed (poetry, Python $(poetry run python -c 'import platform; print(platform.python_version())'))."
else
  echo "WARNING: dependency install incomplete — see /tmp/poetry-install.log. Import tests may fail."
fi
exit 0
