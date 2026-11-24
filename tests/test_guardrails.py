"""Tests for the Claude Code guardrail hooks in .claude/scripts/.

Each hook reads a JSON payload on stdin and exits 0 (allow) or 2 (block). These
tests drive them the same way Claude Code does.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "scripts"


def run_hook(name, tool_input, remote=False):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT)}
    env["CLAUDE_CODE_REMOTE"] = "true" if remote else ""
    return subprocess.run(
        [sys.executable, str(HOOKS / f"{name}.py")],
        input=json.dumps({"tool_input": tool_input}),
        capture_output=True, text=True, env=env, timeout=30,
    )


# --- enforce_safe_commands ---------------------------------------------------

@pytest.mark.parametrize("command", [
    "pip install requests",
    "python -m pip install requests",
    "poetry add py-cord",
    "git push --force origin master",
    "git push -f",
    "git commit --no-verify -m x",
    "git reset --hard HEAD~1",
    "git clean -fd",
    "git checkout -- .",
    "poetry run aerich downgrade",
    "rm -rf build",
    "git add config.py",
    "cat .env",
])
def test_safe_commands_blocks(command):
    assert run_hook("enforce_safe_commands", {"command": command}).returncode == 2


@pytest.mark.parametrize("command", [
    "poetry run pip install pytest",
    "poetry run python -m pip install pytest",
    "git push -u origin claude/x",
    "git commit -m 'add config.example.py'",
    "git add config.example.py",
    "cat config.example.py",
    "ruff check .",
    "echo hi  # rm -rf is dangerous",
])
def test_safe_commands_allows(command):
    assert run_hook("enforce_safe_commands", {"command": command}).returncode == 0


def test_printing_config_py_is_local_only():
    assert run_hook("enforce_safe_commands", {"command": "cat config.py"}).returncode == 2
    assert run_hook("enforce_safe_commands", {"command": "cat config.py"}, remote=True).returncode == 0


# --- file checks ---------------------------------------------------------------

@pytest.fixture
def scratch():
    # Inside the repo so the checks' path filters treat it as project code.
    d = ROOT / "tests" / "_scratch"
    d.mkdir(exist_ok=True)
    yield d
    for f in d.iterdir():
        f.unlink()
    d.rmdir()


def write(dirpath, name, text):
    p = dirpath / name
    p.write_text(text)
    return str(p)


def test_syntax_check(scratch):
    assert run_hook("check_syntax", {"file_path": write(scratch, "ok.py", "x = 1\n")}).returncode == 0
    assert run_hook("check_syntax", {"file_path": write(scratch, "bad.py", "def f(:\n")}).returncode == 2


@pytest.mark.parametrize("code", [
    "intents = discord.Intents.all()\n",
    "intents.members = True\n",
    "intents.message_content = True\n",
    "i = discord.Intents(guilds=True, presences=True)\n",
    "bot = commands.Bot(chunk_guilds_at_startup=True)\n",
    "await guild.chunk()\n",
])
def test_privileged_intents_flagged(scratch, code):
    path = write(scratch, "intents_bad.py", code)
    assert run_hook("check_privileged_intents", {"file_path": path}).returncode == 2


@pytest.mark.parametrize("code", [
    "intents = discord.Intents.default()\n",
    "if not self.bot.intents.message_content:\n    pass\n",
    "intents.members = True  # intents: ok\n",
    "# intents.members = True\n",
])
def test_privileged_intents_allowed(scratch, code):
    path = write(scratch, "intents_ok.py", code)
    assert run_hook("check_privileged_intents", {"file_path": path}).returncode == 0


def test_config_keys(scratch):
    ok = write(scratch, "cfg_ok.py", "import config\nprint(config.DEBUG, config.RACETIME_CLIENT_ID_ALTTPR)\n")
    assert run_hook("check_config_keys", {"file_path": ok}).returncode == 0
    bad = write(scratch, "cfg_bad.py", "import config\nprint(config.SOME_NEW_SETTING)\n")
    result = run_hook("check_config_keys", {"file_path": bad})
    assert result.returncode == 2
    assert "SOME_NEW_SETTING" in result.stderr
    # Not the config module: app.config['X'], self.config.X
    other = write(scratch, "cfg_other.py", "import config\nx = self.config.NOT_OURS\n")
    assert run_hook("check_config_keys", {"file_path": other}).returncode == 0


# --- scripts/guardrails.py ---------------------------------------------------

@pytest.mark.parametrize("base", ["--output=/tmp/x", "-p", "a..b", "origin/master HEAD"])
def test_guardrails_runner_rejects_option_like_base(base):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "guardrails.py"), f"--changed={base}"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert "expects a branch" in result.stderr


# --- check_layers --------------------------------------------------------------

LAYERS = HOOKS / "check_layers.py"


@pytest.fixture
def fake_repo(tmp_path):
    """A throwaway tree with the five packages, so the real allowlist isn't involved."""
    (tmp_path / ".claude" / "scripts").mkdir(parents=True)
    for pkg in ("alttprbot", "alttprbot_discord", "alttprbot_api", "alttprbot_racetime", "alttprbot_audit"):
        (tmp_path / pkg).mkdir()
        (tmp_path / pkg / "__init__.py").write_text("")
    (tmp_path / "alttprbot_discord" / "bot.py").write_text("discordbot = None\n")
    (tmp_path / "alttprbot_discord" / "util").mkdir()
    (tmp_path / "alttprbot_discord" / "util" / "__init__.py").write_text("")
    (tmp_path / "alttprbot_discord" / "util" / "embeds.py").write_text("")
    (tmp_path / "layer_allowlist.txt").write_text("")
    return tmp_path


def run_layers(root, file_path=None, *args):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}
    payload = json.dumps({"tool_input": {"file_path": str(file_path)}}) if file_path else ""
    return subprocess.run(
        [sys.executable, str(LAYERS), *args],
        input=payload, capture_output=True, text=True, env=env, timeout=30,
    )


@pytest.mark.parametrize("rel, code", [
    ("alttprbot/a.py", "from alttprbot_discord.bot import discordbot\n"),
    ("alttprbot/a.py", "import alttprbot_racetime\n"),
    ("alttprbot/a.py", "def f():\n    from alttprbot_discord.util import embeds\n"),
    ("alttprbot_api/a.py", "from alttprbot_discord import bot\n"),
    ("alttprbot_discord/a.py", "from alttprbot_api.util import checks\n"),
    ("alttprbot_audit/a.py", "import alttprbot_discord.util.embeds\n"),
])
def test_layers_flags_cross_layer_import(fake_repo, rel, code):
    path = fake_repo / rel
    path.write_text(code)
    result = run_layers(fake_repo, path)
    assert result.returncode == 2
    assert "layer boundary" in result.stderr


@pytest.mark.parametrize("rel, code", [
    ("alttprbot_discord/a.py", "from alttprbot import models\n"),
    ("alttprbot_api/a.py", "from alttprbot.util import gsheet\nimport config\n"),
    ("alttprbot_discord/a.py", "from .bot import discordbot\nfrom . import util\n"),
    ("alttprbot/a.py", "import discord\nfrom alttprbot.tournament import core\n"),
    ("sahasrahbot.py", "from alttprbot_discord.bot import discordbot\n"),
])
def test_layers_allows_downward_and_internal_imports(fake_repo, rel, code):
    path = fake_repo / rel
    path.write_text(code)
    assert run_layers(fake_repo, path).returncode == 0


def test_layers_submodule_resolution(fake_repo):
    # `from pkg import mod` is an import of pkg.mod, so the allowlist names the module.
    (fake_repo / "layer_allowlist.txt").write_text(
        "# comment -> ignored\nalttprbot.a -> alttprbot_discord.util.embeds  # Phase 1\n"
    )
    path = fake_repo / "alttprbot" / "a.py"
    path.write_text("from alttprbot_discord.util import embeds\n")
    assert run_layers(fake_repo, path).returncode == 0
    assert run_layers(fake_repo, None, "--all").returncode == 0


def test_layers_stale_allowlist_line_fails(fake_repo):
    (fake_repo / "layer_allowlist.txt").write_text("alttprbot.a -> alttprbot_discord.bot\n")
    path = fake_repo / "alttprbot" / "a.py"
    path.write_text("from alttprbot_discord.bot import discordbot\n")
    assert run_layers(fake_repo, path).returncode == 0
    path.write_text("x = 1\n")
    result = run_layers(fake_repo, path)
    assert result.returncode == 2
    assert "no longer match" in result.stderr
    # A deleted importer is only noticed by the whole-tree pass.
    path.unlink()
    assert run_layers(fake_repo, None, "--all").returncode == 2


def test_layers_real_tree_matches_allowlist():
    result = run_layers(ROOT, None, "--all")
    assert result.returncode == 0, result.stderr


# --- check_model_queries -------------------------------------------------------

MODEL_QUERIES = HOOKS / "check_model_queries.py"


def run_model_queries(root, file_path=None, *args):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}
    payload = json.dumps({"tool_input": {"file_path": str(file_path)}}) if file_path else ""
    return subprocess.run(
        [sys.executable, str(MODEL_QUERIES), *args],
        input=payload, capture_output=True, text=True, env=env, timeout=30,
    )


@pytest.mark.parametrize("rel, code", [
    ("alttprbot_discord/a.py", "from alttprbot import models\nasync def f():\n    await models.Users.get_or_none(id=1)\n"),
    ("alttprbot_api/a.py", "from alttprbot import models as m\nasync def f():\n    await m.Presets.filter(x=1).first()\n"),
    ("alttprbot_racetime/a.py", "from alttprbot.models import Users\nasync def f():\n    await Users.create(id=1)\n"),
    ("alttprbot_discord/a.py", "import alttprbot.models\nasync def f():\n    await alttprbot.models.Users.all()\n"),
    ("alttprbot_discord/a.py", "from alttprbot.models import models\nasync def f():\n    await models.X.update_or_create(a=1)\n"),
    ("alttprbot_api/a.py", "from alttprbot import models\nasync def f():\n    await models.X.bulk_create([])\n"),
])
def test_model_queries_flagged(fake_repo, rel, code):
    path = fake_repo / rel
    path.write_text(code)
    result = run_model_queries(fake_repo, path)
    assert result.returncode == 2
    assert "MODEL QUERY" in result.stderr
    assert run_model_queries(fake_repo, None, "--all").returncode == 2


@pytest.mark.parametrize("rel, code", [
    # Annotations and attribute reads on returned models.
    ("alttprbot_racetime/a.py", "from alttprbot import models\nx: models.SpoilerRaces = None\n"),
    ("alttprbot_discord/a.py", "from alttprbot.services import presets\nasync def f():\n    p = await presets.get('a')\n    return p.content\n"),
    # A query method on something that isn't a model class.
    ("alttprbot_api/a.py", "import re\nre.compile('x').match('y')\nd = {}\nd.get('a')\n"),
    ("alttprbot_discord/a.py", "from alttprbot import models\nasync def f(e):\n    await e.candidates.all()\n"),
    # The opt-out, and core code, which may query.
    ("alttprbot_discord/a.py", "from alttprbot import models\nasync def f():\n    await models.X.get(a=1)  # model-query: ok\n"),
    ("alttprbot/a.py", "from alttprbot import models\nasync def f():\n    await models.Users.get(id=1)\n"),
])
def test_model_queries_allowed(fake_repo, rel, code):
    path = fake_repo / rel
    path.write_text(code)
    assert run_model_queries(fake_repo, path).returncode == 0


def test_model_queries_real_tree_is_clean():
    result = run_model_queries(ROOT, None, "--all")
    assert result.returncode == 0, result.stderr
