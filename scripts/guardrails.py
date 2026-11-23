#!/usr/bin/env python3
"""Run the repo's guardrail checks over files on disk, outside Claude Code.

The checks in ``.claude/scripts/`` are wired as Claude Code hooks, so they only
fire on a Write/Edit inside a Claude session. This runner replays each one
against files on disk so CI enforces the same rules for every commit, whoever
wrote it. It does not reimplement any check: it synthesizes the hook payload
each one already parses and reports its exit status.

Usage::

    python3 scripts/guardrails.py --changed origin/master   # PR diff (CI)
    python3 scripts/guardrails.py --all                     # whole tree
    python3 scripts/guardrails.py alttprbot_discord/bot.py  # explicit paths

Exit 0 when every check passes, 1 otherwise. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "scripts"

FILE_CHECKS = [
    "check_syntax",
    "check_privileged_intents",
    "check_config_keys",
]


def tracked_python_files() -> list[str]:
    out = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True, check=True)
    return [f for f in out.stdout.splitlines() if not f.startswith("utils/")]


def changed_python_files(base: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return [f for f in out.stdout.splitlines() if f.endswith(".py") and not f.startswith("utils/")]


def run_check(check: str, rel: str) -> tuple[int, str]:
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(ROOT / rel)}})
    result = subprocess.run(
        [sys.executable, str(HOOKS / f"{check}.py")],
        input=payload, cwd=ROOT, capture_output=True, text=True, timeout=60,
        env={"CLAUDE_PROJECT_DIR": str(ROOT), "PATH": "/usr/bin:/bin"},
    )
    return result.returncode, result.stderr.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="check every tracked .py file")
    group.add_argument("--changed", metavar="BASE", help="check .py files changed since BASE")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()

    if args.all:
        files = tracked_python_files()
    elif args.changed:
        files = changed_python_files(args.changed)
    else:
        files = args.paths
    files = [f for f in files if (ROOT / f).exists()]

    failures = 0
    for rel in files:
        for check in FILE_CHECKS:
            code, err = run_check(check, rel)
            if code == 2:
                failures += 1
                print(f"✗ {check}: {rel}\n{err}\n")
    print(f"guardrails: {len(files)} file(s), {len(FILE_CHECKS)} check(s), {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
