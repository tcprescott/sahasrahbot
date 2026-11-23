#!/usr/bin/env python3
"""
Import-boundary check: stop NEW imports that cross SahasrahBot's layers.

The layers (see the separation-of-concerns plan, Phase 0):

  alttprbot            core: models, seed generation, tournament logic, services
  alttprbot_discord  ┐
  alttprbot_api      │ presentation: one package per front end
  alttprbot_racetime │
  alttprbot_audit    ┘

Two rules:

  1. Core must not import a presentation package.
  2. A presentation package must not import another presentation package.

Presentation may import core. Imports from outside these five packages
(``config``, ``sahasrahbot.py``, third-party code) are not checked.

Every import that already breaks a rule is listed in ``layer_allowlist.txt`` at
the repo root, one ``importer -> imported`` line each. That list only shrinks:
an import not on it fails, and so does a line whose import no longer exists, so
whoever removes a violation also deletes its line. Function-level and
``TYPE_CHECKING`` imports count too, since they couple the code just the same.

Checking direct imports with both rules is enough: any indirect path from one
presentation package to another has to use a direct edge that one of the two
rules forbids.

Modes:
  hook (JSON on stdin, PostToolUse Write|Edit): checks the one edited file.
  ``--all``: checks every module, and that every allowlist line still applies.
  ``--baseline``: prints today's violations in allowlist format, for review.

Exit 0 = clean / not applicable; exit 2 = violation (details on stderr).
"""

from __future__ import annotations

import ast
import json
import sys
import warnings
from pathlib import Path

from _hook_paths import anchor

ROOT = anchor()
ALLOWLIST = ROOT / "layer_allowlist.txt"

CORE = "alttprbot"
PRESENTATION = ("alttprbot_discord", "alttprbot_api", "alttprbot_racetime", "alttprbot_audit")
PACKAGES = (CORE, *PRESENTATION)


def module_name(path: Path) -> str | None:
    """``alttprbot/util/gsheet.py`` → ``alttprbot.util.gsheet``; None outside the packages."""
    try:
        rel = path.resolve().relative_to(ROOT)
    except ValueError:
        return None
    if rel.suffix != ".py" or not rel.parts or rel.parts[0] not in PACKAGES:
        return None
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def is_module(name: str) -> bool:
    base = ROOT.joinpath(*name.split("."))
    return base.with_suffix(".py").is_file() or (base / "__init__.py").is_file()


def resolve_relative(importer: str, is_package: bool, level: int, module: str | None) -> str:
    parts = importer.split(".")
    if not is_package:
        parts = parts[:-1]
    if level > 1:
        parts = parts[: len(parts) - (level - 1)]
    return ".".join(parts + ([module] if module else []))


def imports_of(path: Path, importer: str) -> list[tuple[str, int]]:
    """Every (imported module, line) in the file, at any depth in the code."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)  # old regex strings; not ours to fix here
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []
    is_package = path.name == "__init__.py"
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                base = resolve_relative(importer, is_package, node.level, node.module)
            for alias in node.names:
                # `from pkg import mod` imports the module pkg.mod when one exists.
                sub = f"{base}.{alias.name}" if base else alias.name
                found.append((sub if alias.name != "*" and is_module(sub) else base, node.lineno))
    return found


def forbidden(importer: str, imported: str) -> bool:
    src, dst = importer.split(".")[0], imported.split(".")[0]
    if src == dst or dst not in PRESENTATION:
        return False
    return src == CORE or src in PRESENTATION


def violations_in(path: Path) -> list[tuple[str, str, int]]:
    importer = module_name(path)
    if importer is None:
        return []
    seen: dict[tuple[str, str], int] = {}
    for imported, line in imports_of(path, importer):
        if forbidden(importer, imported):
            seen.setdefault((importer, imported), line)
    return [(a, b, line) for (a, b), line in seen.items()]


def load_allowlist() -> set[tuple[str, str]]:
    entries = set()
    try:
        text = ALLOWLIST.read_text(encoding="utf-8")
    except OSError:
        return entries
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if "->" in line:
            a, b = (s.strip() for s in line.split("->", 1))
            entries.add((a, b))
    return entries


def all_package_files() -> list[Path]:
    files = []
    for pkg in PACKAGES:
        files.extend(sorted((ROOT / pkg).rglob("*.py")))
    return files


def report(new: list[tuple[str, str, int]], stale: list[tuple[str, str]]) -> int:
    if not new and not stale:
        return 0
    lines = []
    if new:
        lines.append("New import across a layer boundary (core must not import a front end; front ends")
        lines.append("must not import each other). Move the shared code into alttprbot/, or pass the")
        lines.append("dependency in from the caller:")
        lines.extend(f"  {a} -> {b}  (line {n})" for a, b, n in sorted(new))
    if stale:
        if lines:
            lines.append("")
        lines.append(f"These {ALLOWLIST.name} lines no longer match any import. Delete them so the")
        lines.append("allowlist keeps shrinking:")
        lines.extend(f"  {a} -> {b}" for a, b in sorted(stale))
    print("\n".join(lines), file=sys.stderr)
    return 2


def check_file(path: Path) -> int:
    importer = module_name(path)
    if importer is None:
        return 0
    allowed = load_allowlist()
    found = violations_in(path)
    new = [v for v in found if (v[0], v[1]) not in allowed]
    present = {(a, b) for a, b, _ in found}
    stale = [e for e in allowed if e[0] == importer and e not in present]
    return report(new, stale)


def check_all() -> int:
    allowed = load_allowlist()
    found = [v for f in all_package_files() for v in violations_in(f)]
    new = [v for v in found if (v[0], v[1]) not in allowed]
    present = {(a, b) for a, b, _ in found}
    stale = [e for e in allowed if e not in present]
    return report(new, stale)


def baseline() -> int:
    found = sorted({(a, b) for f in all_package_files() for a, b, _ in violations_in(f)})
    print("\n".join(f"{a} -> {b}" for a, b in found))
    return 0


def main() -> int:
    if "--all" in sys.argv[1:]:
        return check_all()
    if "--baseline" in sys.argv[1:]:
        return baseline()
    try:
        payload = json.load(sys.stdin)
        file_path = payload["tool_input"]["file_path"]
    except (ValueError, KeyError, TypeError):
        return 0
    if not str(file_path).endswith(".py"):
        return 0
    path = Path(file_path)
    if not path.is_file():
        return 0
    return check_file(path)


if __name__ == "__main__":
    sys.exit(main())
