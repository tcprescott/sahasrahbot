# Tournament Registry Config-Driven Design

> Last updated: 2026-02-12  
> Scope: Replace code-comment seasonal toggles in `alttprbot/tournaments.py` with explicit runtime configuration

## Problem Statement

Current tournament activation is controlled by editing `TOURNAMENT_DATA` in Python source and commenting handlers in/out by season.

Observed issues:

- Operational risk from accidental enable/disable in deploy diffs.
- No runtime visibility of intended active set beyond code inspection.
- Hard to validate config completeness before loops begin creating race rooms.
- Increases merge conflict risk during seasonal transitions.

## Goal

Move event activation and per-event registry metadata into a config-backed source while keeping existing handler classes and race lifecycle behavior unchanged.

Non-goals:

- No redesign of tournament handler class APIs.
- No change to async tournament module behavior.
- No migration of guild/channel IDs out of handler `configuration()` in this phase.

## Reliability Intent

This design is optimized for reliability and operations first:

- Fail fast on invalid config at startup.
- Prefer explicit disabled states over absent/commented code.
- Preserve stable fallback behavior for production safety.

## Proposed Runtime Model

### Source of Truth

Add config file:

- `config/tournaments.yaml`

Runtime load path:

1. Read YAML at startup of tournament subsystem.
2. Validate schema and referenced handler IDs.
3. Build active registry map used by all tournament loops.
4. If validation fails, do not start tournament loops.

### Handler Registration Split

Keep two separate dictionaries in code:

1. `AVAILABLE_TOURNAMENT_HANDLERS`
   - Static map of handler identifiers to import paths/classes.
   - Represents capability.

2. `ACTIVE_TOURNAMENT_REGISTRY`
   - Runtime-built map of event slug to class.
   - Represents policy/seasonal activation.

This preserves explicit code ownership of what handlers exist, while moving activation policy to config.

## YAML Schema (Phase 1)

Top-level keys:

- `version` (integer)
- `profiles` (object)

Required profiles:

- `debug`
- `production`

Each profile contains:

- `events` (list)

Each event object fields:

- `event_slug` (string, unique per profile)
- `handler` (string key into `AVAILABLE_TOURNAMENT_HANDLERS`)
- `enabled` (boolean)
- `notes` (optional string)

Validation rules:

- `event_slug` must be non-empty and URL-safe style.
- `handler` must resolve to known handler key.
- Duplicate `event_slug` is invalid.
- At least one enabled event must exist per profile unless explicitly marked maintenance mode.

## Loader and Validation Behavior

### Loader module

Add module:

- `alttprbot/tournament/registry_loader.py`

Responsibilities:

- Parse YAML.
- Select profile by `config.DEBUG`.
- Validate schema and references.
- Return active dict: event slug to handler class.

### Startup checks

When tournament cog starts:

- Load active registry once.
- Log summary counts: enabled, disabled, invalid.
- If fatal errors exist, surface one consolidated audit message and prevent task loops from running.

### Safe fallback

Initial rollout option:

- Keep legacy hardcoded `TOURNAMENT_DATA` as fallback behind explicit feature flag.
- Default for first release can remain fallback-on to avoid service interruption.

## Migration Plan

### Phase 0: Preparation

- Introduce `AVAILABLE_TOURNAMENT_HANDLERS` in `alttprbot/tournaments.py`.
- Add loader module and schema validation with no runtime switchover.

### Phase 1: Dual-path runtime

- Add `TOURNAMENT_CONFIG_ENABLED` env/config flag.
- If true, build active registry from YAML.
- If false, use existing hardcoded mapping.
- Emit explicit startup log stating which path is active.

### Phase 2: Config-first

- Enable config path in production.
- Keep hardcoded path for one season as emergency rollback only.

### Phase 3: Cleanup

- Remove commented registry blocks.
- Retain only available handler catalog plus config-driven activation.

## Rollback Strategy

If config load fails or causes runtime instability:

1. Disable `TOURNAMENT_CONFIG_ENABLED`.
2. Restart bot to return to hardcoded registry path.
3. Correct YAML and re-enable in next deploy.

Rollback requirement:

- Hardcoded mapping must remain intact until Phase 3 completion.

## Observability Additions

Add structured startup logging fields:

- `registry_source`: config or hardcoded
- `profile`: debug or production
- `enabled_events_count`
- `disabled_events_count`
- `enabled_event_slugs`

Add one audit-channel summary message for startup validation failure when tournament cog is active.

## Open Decisions Requiring Owner Input

1. Should unknown extra YAML keys be treated as warnings or errors?
2. Should empty enabled set be allowed during off-season without maintenance override?
3. Should per-event temporary overrides (for hotfix disable) be allowed through env var list?

## Acceptance Criteria

- Tournament loops consume a runtime registry not hand-edited comment blocks.
- Seasonal enable/disable changes occur in YAML only.
- Invalid handler references are detected before loop execution.
- Production fallback path remains available through explicit flag until cleanup phase.

## Implementation Touchpoints

Expected files when implementation begins:

- `alttprbot/tournaments.py`
- `alttprbot/tournament/registry_loader.py` (new)
- `alttprbot_discord/cogs/tournament.py`
- `config/tournaments.yaml` (new)
- `docs/guides/tournament_module_runbook.md` (update operational procedure)
