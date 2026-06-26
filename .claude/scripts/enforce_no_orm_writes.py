#!/usr/bin/env python3
"""PostToolUse hook: flag direct ORM writes from the presentation tier.

Presentation code (alttprbot/presentation/) may read for display, but writes must
go through a service (which calls a repository). This AST-walks the saved file and
flags a write whose call chain is rooted at a known Tortoise model class — e.g.
``Daily.create(...)`` or ``TournamentResults.filter(...).delete()``. Reads such as
``.filter().order_by()`` are left alone because they don't terminate in a write.

Model class names are loaded from every module in ``alttprbot/models/``.

Mode (notification-only vs blocking) is decided by _hooklib.finish().
"""

import ast
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hooklib  # noqa: E402

WRITE_TERMINALS = {
    "create",
    "bulk_create",
    "get_or_create",
    "update_or_create",
    "bulk_update",
    "update",
    "delete",
    "save",
}


def is_presentation(path: str) -> bool:
    return "/alttprbot/presentation/" in f"/{path.replace(chr(92), '/')}"


def find_repo_root(start_path: str) -> str | None:
    d = os.path.dirname(os.path.abspath(start_path))
    while True:
        if os.path.isdir(os.path.join(d, "alttprbot", "models")) or os.path.isdir(
            os.path.join(d, ".git")
        ):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def load_model_names(repo_root: str) -> set[str]:
    names: set[str] = set()
    models_dir = os.path.join(repo_root, "alttprbot", "models")
    for path in glob.glob(os.path.join(models_dir, "*.py")):
        try:
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = (
                        base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", None)
                    )
                    if base_name == "Model":
                        names.add(node.name)
                        break
    return names


def receiver_model(expr: ast.AST, models: set[str]) -> str | None:
    """Walk a write's receiver chain for a model class name.

    Catches both the bare-class form ``Daily.create(...)`` and the module-qualified
    form ``models.Daily.create(...)`` / ``models.Daily.filter(...).delete()`` used
    throughout SahasrahBot (``from alttprbot import models``).
    """
    while True:
        if isinstance(expr, ast.Attribute):
            if expr.attr in models:
                return expr.attr
            expr = expr.value
        elif isinstance(expr, ast.Call):
            expr = expr.func
        elif isinstance(expr, ast.Name):
            return expr.id if expr.id in models else None
        else:
            return None


def find_violations(tree: ast.AST, models: set[str]) -> list[tuple[int, str, str]]:
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr not in WRITE_TERMINALS:
            continue
        model = receiver_model(func.value, models)
        if model:
            out.append((node.lineno, model, func.attr))
    return out


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path or not file_path.endswith(".py"):
        sys.exit(0)

    norm = file_path.replace(chr(92), "/")
    if "/.claude/" in norm or not is_presentation(file_path):
        sys.exit(0)

    try:
        with open(file_path, encoding="utf-8") as fh:
            source = fh.read()
    except OSError:
        sys.exit(0)

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        sys.exit(0)

    repo_root = find_repo_root(file_path)
    if not repo_root:
        sys.exit(0)
    models = load_model_names(repo_root)
    if not models:
        sys.exit(0)

    violations = [
        f"ARCHITECTURE VIOLATION in '{file_path}' (line {line}):\n"
        f"  Direct ORM write from the presentation tier: {model}.{method}(...)\n"
        f"  Fix: move this write into a service method (which calls the repository)."
        for line, model, method in find_violations(tree, models)
    ]
    _hooklib.finish(violations)


if __name__ == "__main__":
    main()
