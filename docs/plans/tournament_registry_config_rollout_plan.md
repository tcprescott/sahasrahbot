# Plan: Tournament Registry Config-Driven Rollout

> **Status:** Draft  
> **Last updated:** 2026-02-12  
> **Source design:** [Tournament Registry Config-Driven Design](../design/tournament_registry_config_design.md)

## Objective

Replace code-comment seasonal toggles in tournament registry management with validated runtime configuration, while preserving fallback safety during rollout.

## Scope

In scope:

- Runtime activation policy in config (`config/tournaments.yaml`)
- Loader/validation path and profile selection
- Dual-path transition with explicit fallback flag
- Startup observability and operator runbook updates

Out of scope:

- Tournament handler API redesign
- Async tournament module redesign
- Handler `configuration()` guild/channel ID migration in this phase

## Execution Phases

### Phase 0 — Preparation

- Introduce `AVAILABLE_TOURNAMENT_HANDLERS` capability catalog.
- Implement loader module and schema validation without switchover.

### Phase 1 — Dual-Path Runtime

- Add `TOURNAMENT_CONFIG_ENABLED` control flag.
- Route to YAML-backed registry when enabled; preserve hardcoded mapping otherwise.
- Emit startup log indicating active source and profile.

### Phase 2 — Config-First

- Enable config-backed registry in production.
- Keep hardcoded path as emergency fallback for one season.
- Validate operational reliability over full seasonal cycle.

### Phase 3 — Cleanup

- Remove commented registry blocks and legacy activation toggles.
- Keep capability catalog + config-driven activation only.

## Release Gates

1. **Validation Gate:** invalid YAML/handler references fail before loop startup.
2. **Operational Gate:** startup logs clearly show source/profile/enabled set.
3. **Fallback Gate:** hardcoded rollback path remains available until cleanup completes.
4. **Compatibility Gate:** active tournament loops continue with no lifecycle behavior regressions.

### Compatibility Workflow Coverage

This plan must provide gate evidence for the following modernization compatibility workflows:

- Active tournament lifecycle flow
- Tournament registry activation flow
- Bot startup and command registration flow

## Concrete Checklist

- Add `config/tournaments.yaml` schema and debug/production profiles.
- Add `registry_loader.py` with schema/reference validation.
- Add runtime flag and source-selection logic.
- Add startup/audit summary logs for registry status.
- Update tournament operator runbook for config workflow.
- Cutover production to config-first path.
- Remove legacy commented activation blocks after validation window.
- Validate startup source/profile logs and active handler set against configured profile.

## Success Criteria

- Seasonal activation changes happen in config instead of source edits/comments.
- Startup rejects invalid activation config before tournament loops run.
- Rollback remains controlled and explicit through rollout window.
