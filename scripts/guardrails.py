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
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "scripts"

FILE_CHECKS = [
    "check_syntax",
    "check_privileged_intents",
    "check_config_keys",
    "check_layers",
]

# Checks that also need a whole-tree pass, e.g. to notice an allowlist line whose
# importing file was deleted. Run once, with ``--all``, whenever files are checked.
TREE_CHECKS = [
    "check_layers",
]


def tracked_python_files() -> list[str]:
    out = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True, check=True)
    return [f for f in out.stdout.splitlines() if not f.startswith("utils/")]


# A ref name or commit id: no leading dash (so it can't be read as an option),
# no whitespace, no range syntax of its own.
_REF = re.compile(r"^\w[\w./~^-]*$", re.ASCII)


def resolve_base(base: str) -> str:
    """Resolve ``base`` to a commit id, refusing anything that isn't a plain ref."""
    if not _REF.fullmatch(base) or ".." in base:
        raise SystemExit(f"guardrails: --changed expects a branch, tag or commit, got {base!r}")
    out = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{base}^{{commit}}"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise SystemExit(f"guardrails: unknown base {base!r}")
    return out.stdout.strip()


def changed_python_files(base: str) -> list[str]:
    sha = resolve_base(base)
    out = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{sha}...HEAD", "--"],
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


def run_tree_check(check: str) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(HOOKS / f"{check}.py"), "--all"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
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
    if args.all or args.changed:
        for check in TREE_CHECKS:
            code, err = run_tree_check(check)
            if code == 2:
                failures += 1
                print(f"✗ {check} --all\n{err}\n")
    print(f"guardrails: {len(files)} file(s), {len(FILE_CHECKS)} check(s), {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
