#!/usr/bin/env python3
"""PreToolUse hook: enforce the three-tier architecture boundary at edit time.

Reads a Claude Code tool-execution payload from stdin, classifies the target
file by its tier (from its path under ``alttprbot/``), and flags cross-layer
imports in the proposed content.

Boundaries enforced:
  Presentation (alttprbot/presentation/)
    → MUST NOT import alttprbot.repositories
    → MUST NOT import alttprbot.models   (route data access through a service)
  Service (alttprbot/services/)
    → MUST NOT import discord / racetime_bot / quart / alttprbot.presentation
  Repository (alttprbot/repositories/)
    → MUST NOT import alttprbot.services or alttprbot.presentation

Mode (notification-only vs blocking) is decided by _hooklib.finish().
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hooklib  # noqa: E402

FROM_RE = re.compile(r"^\s*from\s+([\w.]+)\s+import\s+(.+)$", re.MULTILINE)
IMPORT_RE = re.compile(r"^\s*import\s+([\w.]+(?:\s*,\s*[\w.]+)*)", re.MULTILINE)


def import_targets(content: str) -> list[str]:
    """Dotted import targets. ``from a.b import c, d`` → a.b, a.b.c, a.b.d."""
    targets: list[str] = []
    for m in FROM_RE.finditer(content):
        module = m.group(1).strip()
        targets.append(module)
        names_part = m.group(2).strip().lstrip("(").rstrip(")")
        for raw in names_part.split(","):
            name = raw.strip().split(" as ")[0].strip()
            if name and name != "*":
                targets.append(f"{module}.{name}")
    for m in IMPORT_RE.finditer(content):
        for raw in m.group(1).split(","):
            mod = raw.strip()
            if mod:
                targets.append(mod)
    return targets


def classify(path: str) -> str | None:
    norm = f"/{path.replace(chr(92), '/')}"
    if "/alttprbot/presentation/" in norm:
        return "presentation"
    if "/alttprbot/services/" in norm:
        return "service"
    if "/alttprbot/repositories/" in norm:
        return "repository"
    return None


def _hits(target: str, prefix: str) -> bool:
    return target == prefix or target.startswith(prefix + ".")


def check(file_path: str, content: str) -> list[str]:
    if not file_path.endswith(".py"):
        return []
    layer = classify(file_path)
    if layer is None:
        return []

    targets = import_targets(content)
    violations: list[str] = []

    if layer == "presentation":
        for t in targets:
            if _hits(t, "alttprbot.repositories"):
                violations.append(
                    f"ARCHITECTURE VIOLATION in '{file_path}':\n"
                    f"  Presentation imports from the repository tier: '{t}'\n"
                    f"  Fix: route data access through alttprbot.services instead."
                )
            if _hits(t, "alttprbot.models"):
                violations.append(
                    f"ARCHITECTURE VIOLATION in '{file_path}':\n"
                    f"  Presentation imports the ORM models directly: '{t}'\n"
                    f"  Fix: call a service; the service uses a repository to reach models."
                )
    elif layer == "service":
        for t in targets:
            for ui in ("discord", "racetime_bot", "quart"):
                if _hits(t, ui):
                    violations.append(
                        f"ARCHITECTURE VIOLATION in '{file_path}':\n"
                        f"  Service tier imports a UI/transport library: '{t}'\n"
                        f"  Fix: keep '{ui}' in the presentation layer; pass plain values "
                        f"into the service or dispatch via a _notify gateway."
                    )
            if _hits(t, "alttprbot.presentation"):
                violations.append(
                    f"ARCHITECTURE VIOLATION in '{file_path}':\n"
                    f"  Service tier imports from the presentation tier: '{t}'\n"
                    f"  Fix: depend on a _notify gateway abstraction, registered by presentation."
                )
    elif layer == "repository":
        for t in targets:
            if _hits(t, "alttprbot.services"):
                violations.append(
                    f"ARCHITECTURE VIOLATION in '{file_path}':\n"
                    f"  Repository tier imports from the service tier: '{t}'\n"
                    f"  Fix: data flows upward — Repository → Service → Presentation."
                )
            if _hits(t, "alttprbot.presentation"):
                violations.append(
                    f"ARCHITECTURE VIOLATION in '{file_path}':\n"
                    f"  Repository tier imports from the presentation tier: '{t}'\n"
                    f"  Fix: repositories are pure data access — remove UI dependencies."
                )

    return violations


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        sys.exit(0)

    if tool_name == "Write":
        content = tool_input.get("content", "")
    elif tool_name == "Edit":
        content = tool_input.get("new_string", "")
    else:
        sys.exit(0)

    if not content:
        sys.exit(0)

    _hooklib.finish(check(file_path, content))


if __name__ == "__main__":
    main()
