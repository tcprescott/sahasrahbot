---
description: Mine this repo's Claude Code session history and git history for recurring bug classes, and add mechanical guardrail hooks that prevent them.
---

Audit this repository's Claude Code **session history** and **git history** for recurring
bug classes, especially ones typical of AI-written code, and add guardrail hooks that
prevent them, following the conventions in `.claude/README.md`.

Work entirely locally. Transcripts may contain secrets: never send them anywhere, and
redact anything sensitive you quote.

## 1. Mine two sources

**Session transcripts** catch bugs introduced and fixed within a session, which never
show up in a commit. Find this repo's folder under `~/.claude/projects/` (the repo's
absolute path with `/` turned into `-`). Each `.jsonl` file is one session. Grep for
signals first (`Traceback`, `ImportError`, `NameError`, `AttributeError`, `SyntaxError`,
failing tests, hook exit-2 messages, users saying "that broke" or "revert"), then read
only the events around each hit.

**Git history**: `git log` for commits with `Co-Authored-By: Claude` or
`Claude-Session:` trailers, and `git show` on fix commits to read the root cause.

## 2. Build a taxonomy

For each bug class: an example, the root cause, and whether an existing hook in
`.claude/scripts/` already covers it. Split them into:

- **Mechanically detectable** with a content regex, an AST check, or a ruff rule. These
  are hook candidates. A new ruff rule family in `ruff.toml` is often the cheapest fix.
- **Not mechanical** (domain logic, external config). Note them; don't force a hook.

## 3. Add a guardrail for each detectable class

- A self-contained script in `.claude/scripts/` that reads the tool JSON from stdin,
  calls `_hook_paths.anchor()`, **fails open** on any ambiguity, and exits 2 with a clear
  stderr message only on a real violation.
- PreToolUse to block a command or write before it happens; PostToolUse for whole-file
  checks; Stop for cross-file sweeps.
- **Low false positives are the cardinal rule.** Run it over the current tree with
  `python3 scripts/guardrails.py --all` before wiring it up: it must report about zero
  false positives, and you should show it would have caught the bug you're targeting.

## 4. Ship

Register each hook in `.claude/settings.json`, add file checks to `FILE_CHECKS` in
`scripts/guardrails.py`, add tests to `tests/test_guardrails.py`, document it in
`.claude/README.md`, and run `./scripts/check.sh`. Finish with a short summary: which bug
class each hook prevents, and its measured false-positive count.
