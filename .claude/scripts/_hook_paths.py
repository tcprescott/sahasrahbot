#!/usr/bin/env python3
"""Repo-root resolution for hook scripts.

Claude Code spawns hooks with the *session's* shell cwd, and that cwd moves
whenever a Bash tool call cd's somewhere else. Anything a hook resolves
relative to cwd — the script path in ``settings.json``, ``Path("tests")``,
``glob("scripts/seed_*.py")``, a bare ``git diff`` — therefore silently points
at the wrong tree, or at no tree at all, the moment the session is working in a
subdirectory. A PreToolUse hook that cannot start exits non-zero, which reads
as "blocked", so a stale cwd bricks every Write/Edit/Bash call in the session.

Every hook script calls :func:`anchor` before touching a path.
"""

import os
import subprocess
from pathlib import Path


def _is_repo(path: Path) -> bool:
    """A candidate is this repo only if it carries the hook tree itself."""
    return (path / ".claude" / "scripts").is_dir()


def _from_env() -> Path | None:
    raw = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(raw).resolve() if raw else None


def _from_script_location() -> Path:
    # <root>/.claude/scripts/_hook_paths.py → <root>
    return Path(__file__).resolve().parents[2]


def _from_git() -> Path | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    return Path(out.stdout.strip()).resolve() if out.returncode == 0 and out.stdout.strip() else None


def repo_root() -> Path:
    """Resolve the repo root without consulting the current working directory.

    ``CLAUDE_PROJECT_DIR`` wins: Claude Code sets it to the session's project
    root, which is the tree the edited files belong to (and is updated when the
    session enters a worktree). The script's own location is the fallback —
    equally cwd-independent, and correct whenever the hook tree was invoked
    from the tree it belongs to. ``git`` and cwd are last-resort guesses that
    only apply if neither of the anchors looks like this repo.
    """
    for candidate in (_from_env(), _from_script_location(), _from_git()):
        if candidate is not None and _is_repo(candidate):
            return candidate
    return Path.cwd()


def anchor() -> Path:
    """Pin the process cwd to the repo root and return it.

    Hook scripts are full of repo-relative paths; rather than rewrite each one,
    make the assumption they encode actually true.
    """
    root = repo_root()
    try:
        os.chdir(root)
    except OSError:
        pass
    return root
