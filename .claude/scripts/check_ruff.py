#!/usr/bin/env python3
"""
PostToolUse hook: run the repo's ruff gate (ruff.toml) on an edited .py file.

The rule set is small on purpose — undefined names, syntax errors, broken
comparisons — so a hit is almost always a real bug, not style. Fails open when
ruff isn't installed (CI runs it regardless).

Exit 0 = clean / not applicable; exit 2 = ruff found something (stderr).
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

from _hook_paths import anchor

ROOT = anchor()


def ruff_command() -> list[str] | None:
    exe = shutil.which("ruff")
    if exe:
        return [exe]
    venv_ruff = ROOT / ".venv" / "bin" / "ruff"
    if venv_ruff.exists():
        return [str(venv_ruff)]
    return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path.endswith(".py") or not Path(file_path).exists():
        sys.exit(0)
    cmd = ruff_command()
    if cmd is None:
        sys.exit(0)

    # --force-exclude makes ruff honour ruff.toml's excludes for an explicit path.
    result = subprocess.run(
        [*cmd, "check", "--force-exclude", "--output-format", "concise", "--no-fix", file_path],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=25,
    )
    if result.returncode == 0:
        sys.exit(0)
    print(f"RUFF ({file_path}):\n{result.stdout.strip()}\n{result.stderr.strip()}".rstrip(), file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
