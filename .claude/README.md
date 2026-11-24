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
  `hooks/lock_requirements.py`, and `racetime-bot` from git. Then it installs the test tooling
  (`requirements-test.txt`) and ruff. Never edits
  `pyproject.toml` or `poetry.lock`.
- **`hooks/session-start.sh`**. Prints the branch, whether a real `config.py` exists, and
  the check command.
- **`hooks/sonar-setup.sh`** (cloud sessions with a `SONAR_TOKEN` only). Installs
  sonarqube-cli, exports `SONARQUBE_CLI_TOKEN`/`_ORG`/`_SERVER` into the session through
  `CLAUDE_ENV_FILE` (the container has no keychain), starts the Docker daemon if it is
  stopped, and runs `sonar integrate claude` from `$HOME` so the MCP server is wired into
  the user-level config, not the repo. The token is a cloud environment secret; never
  commit it. Without one, SonarCloud's web API still works anonymously because the
  project is public. Log: `/tmp/sonar-setup.log`.

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
- **`scripts/check_layers.py`**: blocks new imports across layer boundaries. Core
  (`alttprbot`) must not import a front end (`alttprbot_discord`, `alttprbot_api`,
  `alttprbot_racetime`, `alttprbot_audit`), and front ends must not import each other.
  Imports that already break a rule are listed in
  [`layer_allowlist.txt`](../layer_allowlist.txt), which only shrinks: a line whose
  import is gone also fails, so delete it in the PR that removes the import. With
  `--all` it checks the whole tree; `--baseline` prints today's violations.
- **`scripts/check_model_queries.py`**: in the front ends (`alttprbot_discord`,
  `alttprbot_api`, `alttprbot_racetime`), rejects a Tortoise query method called on a
  model class (`models.Users.get_or_none(...)`, `Presets.filter(...)`, `create`,
  `update_or_create`, `bulk_create`, `all`, `exclude`, `delete`, …). They get data from
  `alttprbot/services/`. Reading a returned model's attributes and type annotations are
  fine. A line can opt out with `# model-query: ok`. `--all` checks every front-end file.

### Stop

- **`scripts/run_tests.py`**: when any `.py` outside `utils/` changed, runs
  `poetry run python -m pytest -q -x tests` (about 35 seconds) and keeps the turn open
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
