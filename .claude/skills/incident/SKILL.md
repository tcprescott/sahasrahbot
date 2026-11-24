---
name: incident
description: >-
  Diagnose and fix a live SahasrahBot problem fast: the bot is offline, a command
  errors, racetime rooms aren't getting seeds, the web app is down, or Sentry is
  alerting. Narrows the cause to a file and line from Sentry and the code, reproduces
  it with a test where possible, and ships the smallest safe fix as a PR to master.
---

# Production incident

SahasrahBot is one process on one asyncio loop (`sahasrahbot.py`): the Discord bot, the
racetime.gg bots and the Quart API share it. One blocking call or one crash at startup
takes everything down. Work in this order and stop as soon as the cause is clear.

## 1. Look before touching code

- **Sentry** (if the Sentry connector is available): search recent unresolved issues and
  open the newest event's stack trace. `SahasrahBotException` is filtered out on purpose,
  so a missing user-facing error is expected. Narrow with the tags (`job`,
  `discord_command`, `racetime_room`, `route`, `release`; see "Sentry" in CLAUDE.md),
  read Sentry Logs around the time, and for "it's slow" check the `loop.lag_p95`,
  `process.cpu` and `loop.stalls` metrics and any `event-loop-blocked` issue first.
- **The bot is completely offline?** Check first for a privileged intent sneaking back in
  (`Intents.all()`, `intents.members = True`, …). Discord rejects the login with close
  code 4014. `python3 scripts/guardrails.py --all` finds it in seconds.
- **Startup crash?** `alttprbot_racetime/bot.py` raises if any racetime category lacks a
  client id or secret, and many modules read `config.X` at import time. Run
  `poetry run python -m pytest -q tests/test_imports.py` to see whether an entry point
  fails to import.
- **Recent change?** `git log --oneline -20 origin/master` and read the diffs that touch
  the failing area.

## 2. Find the line

Read the stack trace's frames in our code (`alttprbot*`), not the library frames. Confirm
the hypothesis by reading the code path end to end before writing anything.

## 3. Fix small

- The smallest change that removes the cause. No refactors during an incident.
- Add a test under `tests/` that fails without the fix, if it can run without Discord or
  the network.
- `./scripts/check.sh`, then a PR to `master` that says what broke, why, and how the fix
  was verified. The user deploys; don't claim it's live.

## 4. Report

Lead with the cause and the PR link. If you couldn't confirm the cause, say what you
checked and what would confirm it.
