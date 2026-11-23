# `.claude/`: Claude Code hooks and guardrails

This directory configures how Claude Code behaves in this repo. The main feature is a
set of **guardrails**: hooks that mechanically enforce the rules in
[`CLAUDE.md`](../CLAUDE.md), so they hold even when the model forgets them.

Everything is wired through [`settings.json`](./settings.json). Checks live in
[`scripts/`](./scripts/), shell hooks in [`hooks/`](./hooks/). In each directory the
underscore-prefixed file (`scripts/_hook_paths.py`, `hooks/_repo.sh`) is shared plumbing:
it resolves the repo root so no hook depends on the session's current directory.

The same file checks run in CI through [`scripts/guardrails.py`](../scripts/guardrails.py),
so they bind every commit, not just ones written in a Claude session. Their own tests are
in [`tests/test_guardrails.py`](../tests/test_guardrails.py).

## How hooks work

Claude Code runs a hook command at a lifecycle event. The hook gets the tool call as JSON
on stdin (`tool_input.file_path`, `tool_input.command`, …) and answers with its exit code:

| Event | When | Exit 2 means |
|---|---|---|
| `SessionStart` | session start | (advisory; stdout becomes context) |
| `PreToolUse` | before a tool runs | **the tool call is blocked** |
| `PostToolUse` | after a tool ran | stderr is fed back to Claude to fix |
| `Stop` | end of a turn | **the turn can't end yet**; stderr is fed back to Claude |

Every check here **fails open**: bad JSON, a missing file, a non-Python path, or a tool
that isn't installed all exit 0. Only a real violation exits 2.

## The hooks

### SessionStart

- **`hooks/install-deps.sh`** (cloud sessions only). Points Poetry at Python 3.13 when
  available and runs `poetry install --no-root`. If that aborts (the proxy refuses
  `racetime-bot`'s archive URL), it installs the locked versions with pip, using
  `hooks/lock_requirements.py`, and `racetime-bot` from git. Then it installs pytest and
  ruff. Never edits
  `pyproject.toml` or `poetry.lock`.
- **`hooks/session-start.sh`**. Prints the branch, whether a real `config.py` exists, and
  the check command.

### PreToolUse (Bash)

- **`scripts/enforce_safe_commands.py`** blocks: bare `pip install` (use `poetry add`, or
  `poetry run pip install` for test tooling), `poetry add py-cord`, force-push,
  `commit --no-verify`, `reset --hard`, `clean -f`, `checkout -- .`, `aerich downgrade`,
  `rm -rf`, committing `.env` or `config.py`, and printing `.env`. On a developer's
  machine it also blocks `DROP TABLE`/`dropdb` and printing `config.py`; in a cloud
  session those have nothing real to protect.

### PostToolUse (Write|Edit)

- **`scripts/check_syntax.py`**: the edited `.py` file must parse.
- **`scripts/check_ruff.py`**: runs `ruff check` with [`ruff.toml`](../ruff.toml) on the
  edited file. The rule set only covers real bugs (undefined names, syntax errors).
- **`scripts/check_privileged_intents.py`**: rejects `Intents.all()`, turning on
  `members`/`presences`/`message_content`, `chunk_guilds_at_startup=True` and
  `guild.chunk()`. Requesting a privileged intent stops the bot from logging in at all.
  A line that only reads a flag can end with `# intents: ok`.
- **`scripts/check_config_keys.py`**: every `config.NAME` read in a module that does
  `import config` must exist in `config.example.py`, because `config.py` is gitignored
  and the example is the only record of the settings.

### Stop

- **`scripts/run_tests.py`**: when any `.py` outside `utils/` changed, runs
  `poetry run python -m pytest -q -x tests` (about 10 seconds) and keeps the turn open
  on failure. Skips if pytest isn't installed.

## Trying a hook by hand

```bash
echo '{"tool_input":{"command":"git push --force"}}' | python3 .claude/scripts/enforce_safe_commands.py; echo $?
echo '{"tool_input":{"file_path":"'"$PWD"'/alttprbot_discord/bot.py"}}' | python3 .claude/scripts/check_privileged_intents.py; echo $?
```

## Adding a guardrail

Use `/guardrail-audit` to find recurring bug classes worth a hook. A new check should be
a self-contained script in `scripts/` that fails open, has near-zero false positives on
the current tree (run `python3 scripts/guardrails.py --all`), is registered in
`settings.json`, is listed in `FILE_CHECKS` in `scripts/guardrails.py` if it checks
files, has a test in `tests/test_guardrails.py`, and is described above.
