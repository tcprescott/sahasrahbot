#!/usr/bin/env python3
from __future__ import annotations

import ast
import sys
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"

SOURCE_DIRS = [
    ROOT / "alttprbot",
    ROOT / "alttprbot_api",
    ROOT / "alttprbot_audit",
    ROOT / "alttprbot_discord",
    ROOT / "alttprbot_racetime",
    ROOT / "helpers",
]

SOURCE_FILES = [
    ROOT / "sahasrahbot.py",
]

MODULE_TO_PACKAGE = {
    "aiofiles": "aiofiles",
    "aiohttp": "aiohttp",
    "aioboto3": "aioboto3",
    "aiocache": "aiocache",
    "aiomysql": "aiomysql",
    "aerich": "aerich",
    "authlib": "authlib",
    "bs4": "beautifulsoup4",
    "dataclasses_json": "dataclasses-json",
    "discord": "discord.py",
    "discord_sentry_reporting": "discord-sentry-reporting",
    "googleapiclient": "google-api-python-client",
    "gspread": "gspread",
    "gspread_asyncio": "gspread-asyncio",
    "html2markdown": "html2markdown",
    "isodate": "isodate",
    "jishaku": "jishaku",
    "markdown": "markdown",
    "marshmallow": "marshmallow",
    "oauth2client": "oauth2client",
    "oauthlib": "oauthlib",
    "pyrankvote": "pyrankvote",
    "pytz": "pytz",
    "pyz3r": "pyz3r",
    "quart": "quart",
    "quart_discord": "Quart-Discord",
    "racetime_bot": "racetime-bot",
    "sentry_sdk": "sentry-sdk",
    "slugify": "python-slugify",
    "tenacity": "tenacity",
    "tortoise": "tortoise-orm",
    "urlextract": "urlextract",
    "werkzeug": "werkzeug",
    "yaml": "PyYAML",
    "dateutil": "python-dateutil",
}

IGNORED_MODULES = {
    "config",
    "alttprbot",
    "alttprbot_api",
    "alttprbot_audit",
    "alttprbot_discord",
    "alttprbot_racetime",
    "migrations",
    "helpers",
    "util",
    "data",
}


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for source_dir in SOURCE_DIRS:
        if source_dir.exists():
            for path in source_dir.rglob("*.py"):
                if "/__pycache__/" in path.as_posix():
                    continue
                files.append(path)
    for source_file in SOURCE_FILES:
        if source_file.exists():
            files.append(source_file)
    return files


def parse_imports(path: Path) -> set[str]:
    content = path.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                modules.add(node.module.split(".")[0])
    return modules


def workspace_top_level_modules() -> set[str]:
    result: set[str] = set()
    for child in ROOT.iterdir():
        if child.name.startswith("."):
            continue
        if child.is_dir():
            result.add(child.name)
            init_file = child / "__init__.py"
            if init_file.exists():
                result.add(child.name)
        elif child.suffix == ".py":
            result.add(child.stem)
    return result


def load_declared_packages() -> set[str]:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    deps = data["tool"]["poetry"]["dependencies"]
    return set(deps.keys())


def main() -> int:
    stdlib_modules = set(sys.stdlib_module_names)
    local_modules = workspace_top_level_modules()
    declared_packages = load_declared_packages()

    imported_modules: set[str] = set()
    for path in iter_python_files():
        imported_modules |= parse_imports(path)

    candidate_modules = {
        module
        for module in imported_modules
        if module not in stdlib_modules
        and module not in local_modules
        and module not in IGNORED_MODULES
    }

    missing_packages: dict[str, str] = {}
    unmapped_modules: set[str] = set()

    for module in sorted(candidate_modules):
        package = MODULE_TO_PACKAGE.get(module)
        if not package:
            unmapped_modules.add(module)
            continue
        if package not in declared_packages:
            missing_packages[module] = package

    if not missing_packages and not unmapped_modules:
        print("Dependency declaration guard passed: all imported third-party modules are declared.")
        return 0

    if missing_packages:
        print("Missing declared dependencies for imported modules:")
        for module, package in missing_packages.items():
            print(f"  - module '{module}' -> package '{package}'")

    if unmapped_modules:
        print("Unmapped third-party modules detected (update MODULE_TO_PACKAGE):")
        for module in sorted(unmapped_modules):
            print(f"  - {module}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
