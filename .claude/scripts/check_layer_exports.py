#!/usr/bin/env python3
"""PostToolUse hook: new services/repositories must be exported from __init__.py.

When a ``<Name>Service`` is added to ``alttprbot/services/`` (or a subpackage) or a
``<Name>Repository`` to ``alttprbot/repositories/``, this verifies the
filename-derived primary class is both imported and listed in ``__all__`` of the
sibling ``__init__.py``.

Mode (notification-only vs blocking) is decided by _hooklib.finish().
"""

import ast
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hooklib  # noqa: E402


def package_for(norm: str) -> str | None:
    base = os.path.basename(norm)
    if base == "__init__.py" or not base.endswith(".py"):
        return None
    slashed = f"/{norm}"
    if base.endswith("_service.py") and "/alttprbot/services/" in slashed:
        return os.path.dirname(norm)
    if base.endswith("_repository.py") and "/alttprbot/repositories/" in slashed:
        return os.path.dirname(norm)
    return None


def expected_class_name(norm: str) -> str:
    stem = os.path.basename(norm)[:-3]
    return "".join(part.capitalize() for part in stem.split("_"))


def primary_class(source: str, expected: str) -> str | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == expected:
            return node.name
    return None


def exported_names(init_source: str) -> tuple[set[str], set[str]]:
    imported: set[str] = set()
    all_names: set[str] = set()
    try:
        tree = ast.parse(init_source)
    except SyntaxError:
        return imported, all_names
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported.add(alias.asname or alias.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                all_names.add(elt.value)
    return imported, all_names


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path:
        sys.exit(0)

    norm = file_path.replace(chr(92), "/")
    package_dir = package_for(norm)
    if package_dir is None:
        sys.exit(0)

    expected = expected_class_name(norm)
    try:
        with open(file_path, encoding="utf-8") as fh:
            cls = primary_class(fh.read(), expected)
    except OSError:
        sys.exit(0)
    if cls is None:
        sys.exit(0)

    init_path = os.path.join(package_dir, "__init__.py")
    try:
        with open(init_path, encoding="utf-8") as fh:
            imported, all_names = exported_names(fh.read())
    except OSError:
        imported, all_names = set(), set()

    if cls not in imported or cls not in all_names:
        _hooklib.finish(
            [
                f"EXPORT CONVENTION VIOLATION in '{file_path}':\n"
                f"  {cls} is defined but not exported from '{init_path}'.\n"
                f"  Add `from .{os.path.basename(norm)[:-3]} import {cls}` and list it in __all__."
            ]
        )
    sys.exit(0)


if __name__ == "__main__":
    main()
