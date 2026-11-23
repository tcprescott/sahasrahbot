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
