#!/usr/bin/env python3
"""
PostToolUse hook: every ``config.X`` the code reads must exist in config.example.py.

The real ``config.py`` is gitignored, so the only list of settings anyone (or
any agent, or CI) can see is ``config.example.py``. A new ``config.FOO`` that
isn't added there breaks the import smoke tests in CI and leaves the next
person guessing what to set in production.

Only literal attribute reads (``config.FOO``) are checked; dynamic
``getattr(config, ...)`` lookups are out of scope.

Exit 0 = clean / not applicable; exit 2 = missing keys (details on stderr).
"""

import json
import re
import sys
from pathlib import Path

from _hook_paths import anchor

ROOT = anchor()
EXAMPLE = ROOT / "config.example.py"

# `config.FOO` where `config` is the module (not `self.config`, `app.config`, …).
CONFIG_READ = re.compile(r"(?<![\w.])config\.([A-Z][A-Z0-9_]*)\b")


def example_keys() -> set[str]:
    namespace: dict = {}
    exec(compile(EXAMPLE.read_text(encoding="utf-8"), str(EXAMPLE), "exec"), namespace)
    return {k for k in namespace if k.isupper()}


def imports_config(text: str) -> bool:
    return re.search(r"^\s*import config\b", text, re.MULTILINE) is not None


def missing_keys(text: str, known: set[str]) -> list[tuple[int, str]]:
    if not imports_config(text):
        return []
    out = []
    for lineno, line in enumerate(text.splitlines(), 1):
        code = line.split("#", 1)[0]
        for key in CONFIG_READ.findall(code):
            if key not in known:
                out.append((lineno, key))
    return out


def applies(path: str) -> bool:
    if not path.endswith(".py"):
        return False
    try:
        rel = Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return False
    return not (rel.startswith("utils/") or rel.startswith(".claude/") or rel == "config.example.py")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path or not applies(file_path) or not EXAMPLE.exists():
        sys.exit(0)
    try:
        text = Path(file_path).read_text(encoding="utf-8")
        known = example_keys()
    except (OSError, SyntaxError):
        sys.exit(0)

    missing = missing_keys(text, known)
    if not missing:
        sys.exit(0)

    print(f"CONFIG KEY not in config.example.py ('{file_path}'):", file=sys.stderr)
    for lineno, key in missing:
        print(f"  line {lineno}: config.{key}", file=sys.stderr)
    print(
        "  config.py is gitignored, so config.example.py is the only record of the settings.\n"
        "  Add each key there with a harmless placeholder and a short comment, and tell the\n"
        "  user it needs a real value in production.",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
