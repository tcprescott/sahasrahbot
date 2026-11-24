#!/usr/bin/env python3
"""
PostToolUse hook: front ends must not query the database themselves.

``alttprbot_discord/``, ``alttprbot_api/`` and ``alttprbot_racetime/`` reach the
database through ``alttprbot/services/``. This check rejects a Tortoise query
method called on a model class in those packages:

    await models.Users.get_or_none(discord_user_id=...)      # rejected
    await Presets.filter(randomizer='alttpr').all()          # rejected (imported model)

Reading attributes of a model a service returned is fine, and so are type
annotations (``spoiler_race: models.SpoilerRaces``). Calls on a model *instance*
(``election.save()``) can't be told apart from other calls statically and aren't
checked; keep those in services too.

A line can opt out with a trailing ``# model-query: ok`` comment, for a reason
written next to it.

Exit 0 = clean / not applicable; exit 2 = violation (details on stderr).
"""

from __future__ import annotations

import ast
import json
import re
import sys
import warnings
from pathlib import Path

from _hook_paths import anchor

ROOT = anchor()

FRONT_ENDS = ("alttprbot_discord", "alttprbot_api", "alttprbot_racetime")

# Modules whose attributes are model classes.
MODEL_MODULES = ("alttprbot.models", "alttprbot.models.models", "alttprbot.models.schedule")

# Class-level Tortoise entry points: each starts a query or writes rows.
QUERY_METHODS = frozenset({
    "all", "annotate", "bulk_create", "bulk_update", "count", "create", "delete", "exclude",
    "exists", "filter", "first", "get", "get_or_create", "get_or_none", "in_bulk", "raw",
    "select_for_update", "update_or_create",
})

OPT_OUT = re.compile(r"#\s*model-query:\s*ok\b")


def applies(path: str) -> bool:
    if not path.endswith(".py"):
        return False
    try:
        rel = Path(path).resolve().relative_to(ROOT)
    except ValueError:
        return False
    return bool(rel.parts) and rel.parts[0] in FRONT_ENDS


def _bindings(tree: ast.AST) -> tuple[set[str], set[str]]:
    """Names bound to a models module (``models``) and to a model class (``Presets``)."""
    modules: set[str] = set()
    classes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for alias in node.names:
                bound = alias.asname or alias.name
                if f"{node.module}.{alias.name}" in MODEL_MODULES:
                    modules.add(bound)
                elif node.module in MODEL_MODULES and alias.name != "*":
                    classes.add(bound)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in MODEL_MODULES:
                    # ``import alttprbot.models`` binds ``alttprbot``; ``_is_model_class``
                    # matches the full dotted path, so record the path itself.
                    modules.add(alias.asname or alias.name)
    return modules, classes


def _dotted(node: ast.AST) -> str | None:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return ".".join(reversed(parts))


def _is_model_class(node: ast.AST, modules: set[str], classes: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in classes
    if isinstance(node, ast.Attribute):
        owner = _dotted(node.value)
        return owner is not None and (owner in modules or owner in MODEL_MODULES)
    return False


def scan(text: str) -> list[tuple[int, str]]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return []
    modules, classes = _bindings(tree)
    if not modules and not classes:
        return []
    lines = text.splitlines()
    hits = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr not in QUERY_METHODS or not _is_model_class(node.func.value, modules, classes):
            continue
        line = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
        if OPT_OUT.search(line):
            continue
        hits.append((node.lineno, line.strip()))
    return sorted(hits)


def check_file(path: Path) -> list[tuple[int, str]]:
    try:
        return scan(path.read_text(encoding="utf-8"))
    except OSError:
        return []


def report(file_path: str, hits: list[tuple[int, str]]) -> None:
    print(f"MODEL QUERY IN A FRONT END: '{file_path}'", file=sys.stderr)
    for lineno, line in hits:
        print(f"  line {lineno}: {line}", file=sys.stderr)
    print(
        "  alttprbot_discord/, alttprbot_api/ and alttprbot_racetime/ get their data from\n"
        "  alttprbot/services/. Move the query into a service function that takes plain\n"
        "  values (see alttprbot/services/guild_config.py) and call that instead.",
        file=sys.stderr,
    )


def check_all() -> int:
    failed = False
    for pkg in FRONT_ENDS:
        for path in sorted((ROOT / pkg).rglob("*.py")):
            hits = check_file(path)
            if hits:
                report(str(path.relative_to(ROOT)), hits)
                failed = True
    return 2 if failed else 0


def main() -> int:
    if "--all" in sys.argv[1:]:
        return check_all()
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path or not applies(file_path):
        return 0
    hits = check_file(Path(file_path))
    if not hits:
        return 0
    report(file_path, hits)
    return 2


if __name__ == "__main__":
    sys.exit(main())
