# Agent guide

**[CLAUDE.md](CLAUDE.md) is canonical.** Read it before writing code. It has the standing
facts (no privileged intents, audit bot removed, async tournaments kept), the layout map,
setup, the check command, and the coding conventions.

- `./scripts/check.sh` runs what CI runs: ruff, the guardrail checks, and pytest.
- `.claude/` holds the hooks that enforce the rules at write time; see
  [`.claude/README.md`](.claude/README.md) for what each one checks.
- `docs/` is the public user site, not developer documentation.
