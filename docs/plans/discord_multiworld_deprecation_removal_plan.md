# Plan: Discord Multiworld Deprecation & Removal

> **Status:** Draft  
> **Last updated:** 2026-02-12  
> **Source design:** [Discord Multiworld Deprecation Audit](../design/discord_multiworld_deprecation_audit.md)

## Objective

Retire Discord multiworld command surfaces (`smmulti`, `doorsmw`, legacy `bontamw`) on a controlled timeline, with explicit user messaging and coordinated schema cleanup.

## Scope

In scope:

- `alttprbot_discord/cogs/smmulti.py`
- `alttprbot_discord/cogs/doorsmw.py`
- `alttprbot_discord/cogs/bontamw.py` (dead/disabled cleanup)
- `alttprbot_discord/bot.py` extension loading
- `alttprbot/models/models.py` (`Multiworld`, `MultiworldEntrant`, `SMZ3Multiworld`)
- Associated database tables (`multiworld`, `multiworldentrant`, `smz3_multiworld`)

Out of scope:

- Broad RaceTime/tournament multiworld retirement
- Replacement Discord multiworld feature (confirmed none)

## Execution Phases

### Phase A — Soft Deprecation (current release)

- Keep command surfaces callable but return deprecation/retirement message contract.
- Announce removal timeline and migration guidance (retired feature, no replacement).
- Freeze new investments in Discord multiworld code.

### Phase B — Functional Removal (next release)

- Remove extension loads for `smmulti` and `doorsmw`.
- Remove retired command modules and keep `bontamw` deleted or permanently retired.
- Validate command sync to ensure retired groups are no longer registered.

### Phase C — Data Contract Cleanup (next release)

- Remove multiworld ORM models.
- Apply migrations dropping `multiworld`, `multiworldentrant`, and `smz3_multiworld`.
- Remove stale references in docs/context after removal lands.

## Release Gates

1. **Messaging Gate:** in-command deprecation messaging live before removal.
2. **Runtime Gate:** Discord startup and command sync pass without multiworld cogs.
3. **Schema Gate:** table drops sequenced after command/cog retirement.
4. **Dependency Gate:** shared generator callers outside Discord remain documented and unaffected.

## Concrete Checklist

- Add deprecation response text to active Discord multiworld commands.
- Publish deprecation window and removal date.
- Remove `smmulti` and `doorsmw` extension loads.
- Delete retired cog modules and cleanup dead `bontamw` code.
- Drop multiworld-related models/tables via migration.
- Validate non-multiworld generation and startup behavior.
- Re-audit RaceTime/tournament multiworld dependency if broader retirement is later planned.

## Success Criteria

- Discord multiworld hosting commands are fully retired.
- Confirmed data policy executed (drop without archival).
- Non-Discord shared generation paths remain stable.
