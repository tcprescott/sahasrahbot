#!/usr/bin/env python3
"""
PostToolUse hook: reject a Write/Edit that leaves a .py file syntactically invalid.

Runs *after* the file is on disk, so it validates the real result of both a
whole-file Write and a fragment Edit. On a SyntaxError it prints the location to
stderr and exits 2 (Claude Code surfaces this so the model fixes it). Anything
else — non-Python, unreadable file, valid syntax — exits 0 (fail open).
"""

import ast
import json
import sys

from _hook_paths import anchor

anchor()  # hooks inherit the session's shell cwd; pin paths to the repo


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path or not file_path.endswith(".py"):
        sys.exit(0)

    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            source = fh.read()
    except OSError:
        sys.exit(0)

    try:
        ast.parse(source, filename=file_path)
    except SyntaxError as exc:
        line = exc.lineno if exc.lineno is not None else "?"
        col = exc.offset if exc.offset is not None else "?"
        print(
            f"SYNTAX ERROR in '{file_path}' (line {line}, col {col}): {exc.msg}\n"
            f"  This change left the file unparseable. Fix the syntax before continuing.",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
