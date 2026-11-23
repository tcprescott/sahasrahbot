#!/usr/bin/env python3
"""
Stop hook: run the test suite before a turn ends, if Python source changed.

Gated so idle turns stay fast: only runs when the working tree, the index, or
untracked files contain a changed ``.py`` outside utils/. The suite is small
(import smoke, guardrail and unit tests, ~35s), so it runs whole.

Fails open when pytest isn't installed in the project venv: the session-start
hook installs it in cloud sessions, and CI runs the suite regardless.

Exit 0 = passed / nothing relevant changed / can't run; exit 2 = failures
(output on stderr so Claude fixes them before ending the turn).
"""

import json
import subprocess
import sys

from _hook_paths import anchor

ROOT = anchor()
TIMEOUT = 170


def changed_python_files() -> list[str]:
    cmds = [
        ["git", "diff", "--name-only"],
        ["git", "diff", "--name-only", "--cached"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    files: set[str] = set()
    for cmd in cmds:
        try:
            out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=10)
        except (subprocess.SubprocessError, OSError):
            continue
        files.update(line.strip() for line in out.stdout.splitlines() if line.strip())
    return sorted(f for f in files if f.endswith(".py") and not f.startswith("utils/"))


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = {}
    # Don't loop: if this hook already blocked once this turn, let the turn end.
    if payload.get("stop_hook_active"):
        sys.exit(0)

    if not changed_python_files():
        sys.exit(0)

    probe = subprocess.run(
        ["poetry", "run", "python", "-c", "import pytest"],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    if probe.returncode != 0:
        sys.exit(0)

    try:
        result = subprocess.run(
            ["poetry", "run", "python", "-m", "pytest", "-q", "-x", "tests"],
            cwd=ROOT, capture_output=True, text=True, timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        print(f"TESTS: pytest did not finish within {TIMEOUT}s.", file=sys.stderr)
        sys.exit(2)

    if result.returncode in (0, 5):  # 5 = no tests collected
        sys.exit(0)
    print(
        "TESTS FAILED (poetry run python -m pytest -q tests):\n" + result.stdout[-6000:] + result.stderr[-2000:],
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
