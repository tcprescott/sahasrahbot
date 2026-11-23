"""Smoke test: every entry point imports cleanly.

This is the cheapest check that catches the bugs most likely to slip through
in a codebase with few tests: a typo'd import, a renamed symbol, a circular
import, a new ``config.X`` that ``config.example.py`` doesn't define, or a
dependency upgrade that removed an API. Each module is imported in a fresh
interpreter, the way ``sahasrahbot.py`` would, so one module's import side
effects can't mask another's failure.

If this fails with ``module 'config' has no attribute ...``, add the new
setting to ``config.example.py``.
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

ENTRY_POINTS = [
    "alttprbot.models",
    "alttprbot_discord.bot",
    "alttprbot_racetime.bot",
    "alttprbot_api.api",
    "alttprbot_audit.bot",
]

_RUNNER = """
import sys
sys.path.insert(0, {root!r})
sys.path.insert(0, {tests!r})
import conftest  # installs config.example.py as `config` and stubs Google clients
import importlib
importlib.import_module({module!r})
"""


@pytest.mark.parametrize("module", ENTRY_POINTS)
def test_entry_point_imports(module):
    code = _RUNNER.format(root=str(ROOT), tests=str(ROOT / "tests"), module=module)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"importing {module} failed:\n{result.stderr[-4000:]}"


def test_discord_bot_requests_no_privileged_intents():
    """Privileged intents are permanently off (see CLAUDE.md)."""
    code = _RUNNER.format(root=str(ROOT), tests=str(ROOT / "tests"), module="alttprbot_discord.bot") + """
from alttprbot_discord.bot import discordbot
i = discordbot.intents
assert not (i.members or i.presences or i.message_content), i
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr[-4000:]


def _discord_extensions():
    """Every cog alttprbot_discord/bot.py loads (live lines, not commented out)."""
    import re

    text = (ROOT / "alttprbot_discord" / "bot.py").read_text()
    live = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    return [m for m in re.findall(r"load_extension\(\s*['\"]([\w.]+)['\"]", live) if m.startswith("alttprbot")]


@pytest.mark.parametrize("module", _discord_extensions())
def test_discord_cog_imports(module):
    """Cogs are loaded lazily by load_extensions(), so the bot.py import doesn't cover them."""
    code = _RUNNER.format(root=str(ROOT), tests=str(ROOT / "tests"), module=module)
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, f"importing {module} failed:\n{result.stderr[-4000:]}"
