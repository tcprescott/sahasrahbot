# Plan: Application Modernization Vision (2026–2027)

> **Status:** Draft  
> **Last updated:** 2026-02-12  
> **Planning Horizon:** 24 months (2026–2027)  
> **Target Topology:** Modular monolith (single deployment, strongly bounded modules)

## 1. Vision

Modernize SahasrahBot into a **reliable, secure, observable modular monolith** that preserves existing community-critical functionality while safely removing legacy/dead-weight paths and reducing change risk.

This plan is the umbrella roadmap that aligns existing execution plans (Discord refactor, telemetry rollout, provider reliability, tournament config migration) under one decision framework and sequencing model.

## 2. Confirmed Strategic Priorities

From owner guidance (2026-02-12):

1. **Security hardening**
2. **Operational observability**
3. **Developer velocity**
4. **Migration risk minimization** as the governing constraint

### 2.1 Explicit Non-Goals (Through Phase C)

- No multi-service decomposition or distributed deployment split before Phase D checkpoint.
- No broad feature expansion in high-risk surfaces until WS1/WS2 gates pass.
- No permanent dual-path behavior without dated deprecation/sunset criteria.

## 3. Modernization Principles

1. **Risk-first migration:** Prefer strangler/incremental replacement over large rewrites.
2. **Boundary before split:** Enforce module contracts in-process before any service decomposition decision.
3. **Default secure runtime:** Eliminate insecure defaults and implicit trust assumptions.
4. **Observe before optimize:** Add shared telemetry/error taxonomy prior to broad refactors.
5. **Deprecate explicitly:** Every legacy feature gets owner, timeline, and removal criteria.
6. **No dual-path drift:** Temporary compatibility windows must have sunset dates.

## 4. Target 2027 State (Modular Monolith)

### 4.1 Module Boundaries

- **Domain Core:** seed generation, tournament lifecycle, policy contracts
- **Platform Adapters:** Discord, RaceTime, Web/API presentation/integration layers
- **Infrastructure Services:** persistence, config, cache, telemetry, retries/timeouts
- **Operations Layer:** startup supervision, health checks, diagnostics, runbooks

### 4.2 Contract Rules

- No cross-layer imports from infrastructure/data modules into presentation adapters.
- All external-provider calls use shared reliability contract (timeouts/retries/error normalization).
- Startup orchestration follows supervised lifecycle contract (fail-fast for critical services, degraded mode only when explicitly allowed).
- Config access runs through explicit service interfaces (no monkey-patching).

## 5. Portfolio Workstreams

### WS1 — Runtime Security Baseline (Priority: P0)

- Remove insecure OAuth transport from non-local runtime paths.
- Enforce non-empty app secret and startup validation checks.
- Complete secrets rotation/revocation workflow and documentation.
- Add security-focused config audit at startup (required/optional env keys).
- Deliver phased Discord OAuth migration from `Quart-Discord` to `Authlib` with dual-path rollback window.

### WS2 — Observability and Operations (Priority: P0)

- Implement shared anonymous telemetry MVP and retention policy.
- Standardize error taxonomy and provider failure classification.
- Add startup supervision strategy and subsystem health instrumentation.
- Publish operational dashboards/queries for daily reliability review.

### WS3 — Configuration and Boundary Hardening (Priority: P1)

- Deliver `GuildConfigService` migration and remove guild monkey-patching.
- Complete channel-name to channel-ID migration.
- Consolidate seasonal toggles into validated runtime config.
- Define clear ownership of config, cache, and persistence layers.

### WS4 — Legacy Surface Reduction (Priority: P1)

- Execute role-assignment deprecation/removal plan.
- Execute multiworld Discord deprecation/removal plan.
- Establish quarterly dead-weight review to retire inactive feature paths.
- Track removals with migration notes and rollback windows.

### WS5 — Developer Velocity Foundation (Priority: P2)

- Reconcile declared dependencies with runtime imports.
- Introduce minimum quality gates (lint + targeted smoke validation).
- Expand type coverage on cross-module interfaces first.
- Incrementally improve module-level testability for core flows.

### 5.1 Workstream Dependency Map

- WS2 depends on WS1 startup/config hardening decisions for reliable signal quality.
- WS3 depends on WS2 error taxonomy and telemetry envelopes for migration safety.
- WS4 depends on WS3 config boundary hardening to avoid removing paths still carrying hidden coupling.
- WS5 should begin in parallel, but quality gates become required at Phase B entry.

## 6. Phased Roadmap

### Phase A (Q1–Q2 2026): Stabilize and Secure

- WS1 + WS2 baseline delivered.
- No net-new high-risk feature surface until security/observability gates pass.

### Phase B (Q2–Q3 2026): Boundaries and Config Migration

- WS3 delivered with compatibility windows and rollback plans.
- Tournament/config loader and seed-provider reliability wrappers operational.

### Phase C (Q3–Q4 2026): Legacy Reduction and Policy Simplification

- WS4 deprecations finalized; dead paths removed.
- Cross-surface behavior contracts documented and enforced.

### Phase D (2027): Performance and Optional Deployment Evolution

- Optimize hotspots using telemetry evidence.
- Re-evaluate process split feasibility only if module contracts are stable and operationally justified.

### 6.1 Phase Exit Criteria (Required to Advance)

- **Exit A → B:** startup validation blocks insecure runtime defaults; baseline telemetry and health checks visible in operations dashboard; rollback notes published for WS1/WS2 changes.
- **Exit B → C:** `GuildConfigService` migration shipped with compatibility window + sunset date; channel-ID migration complete for targeted guild config keys; provider wrapper adopted in primary seed-generation paths.
- **Exit C → D:** role assignment and multiworld removals completed per deprecation policy; dead-path removal impact report published; no unresolved critical compatibility regressions in user-critical workflows.

## 7. Decision Gates (Risk Controls)

Each phase/workstream must pass:

1. **Compatibility Gate:** Existing critical commands/workflows remain functional.
2. **Observability Gate:** New path emits measurable success/failure signals.
3. **Rollback Gate:** Documented rollback or feature-flag fallback exists.
4. **Security Gate:** No insecure defaults introduced or retained.

Gate evidence is mandatory and should be recorded per workstream in execution plan checklists (test/smoke notes, telemetry screenshots/queries, rollback procedure, security validation output).

### 7.1 Compatibility Gate Workflow Set (Phase A Baseline)

The following workflows are the authoritative baseline set for modernization compatibility checks:

1. **Discord seed rolling:** user-triggered seed generation completes with expected success/error response contract.
2. **RaceTime seed rolling:** race room generation path executes with provider response and operator-visible outcome.
3. **API seed generation endpoint:** web/API generation path returns expected payload/error semantics.
4. **Discord daily challenge flow:** scheduled/manual daily generation and posting path remains operational.
5. **Active tournament lifecycle flow:** create room/invite/roll/report sequence remains intact for currently active tournament handlers.
6. **Tournament registry activation flow:** configured seasonal enable/disable policy applies correctly at startup.
7. **Bot startup and command registration flow:** Discord startup succeeds and expected command groups are available.
8. **Critical provider failure handling flow:** timeout/retry/normalized error behavior is visible and actionable without uncaught runtime failure.

Each workstream plan must map which subset of this baseline is required evidence for its release gate.

## 8. Success Metrics

- Startup failures become explicit, observable, and actionable (no silent subsystem degradation).
- Security posture: no insecure transport/default-empty-secret in non-local runtime.
- Coverage: top user-critical flows instrumented with normalized outcomes.
- Change safety: deprecations/removals executed with documented impact and low incident rate.
- Developer efficiency: reduced time-to-safely-change high-traffic modules.

### 8.1 Metrics Clarification (Leading vs Lagging)

- **Leading indicators:** gate pass rate by phase, percentage of migrated paths using shared provider reliability contract, percentage of startup paths under supervision contract.
- **Lagging indicators:** incident count tied to modernization changes, rollback frequency, mean time to detect and triage subsystem startup/provider failures.

Target thresholds should be set during Phase A checkpoint once baseline telemetry is live.

## 9. Plan Relationships

This vision plan governs and sequences:

- [Discord Refactor](discord_refactor.md)
- [Anonymous Telemetry & User Stats Plan](anonymous_telemetry_user_stats_plan.md)
- [Seed Provider Reliability Contract Implementation](seed_provider_reliability_implementation_plan.md)
- [Tournament Registry Config-Driven Rollout](tournament_registry_config_rollout_plan.md)
- [Discord Role Assignment Deprecation & Removal](discord_role_assignment_deprecation_removal_plan.md)
- [Discord Multiworld Deprecation & Removal](discord_multiworld_deprecation_removal_plan.md)
- [Modernization Compatibility Gate Validation Runbook](modernization_compatibility_gate_validation_runbook.md)
- [Authlib Migration for Discord OAuth](authlib_discord_oauth_migration_plan.md)

Design references informing these plans:

- [Seed Provider Reliability Contract](../design/seed_provider_reliability_contract.md)
- [Tournament Registry Config-Driven Design](../design/tournament_registry_config_design.md)
- [Discord Role Assignment Deprecation Audit](../design/discord_role_assignment_deprecation_audit.md)
- [Discord Multiworld Deprecation Audit](../design/discord_multiworld_deprecation_audit.md)

## 10. Governance Cadence

- **Bi-weekly:** modernization checkpoint against risk, incident trends, and blocked migrations.
- **Monthly:** dead-weight review and deprecation scoreboard update.
- **Quarterly:** architecture checkpoint for modular boundary health and optional topology reassessment.

## 11. Top Risks and Mitigations

- **Hidden coupling risk:** legacy cross-layer imports and monkey-patching can cause migration regressions.
	- **Mitigation:** enforce boundary scans/reviews before WS3 rollouts and keep compatibility windows explicit.
- **Observability blind spots:** migration changes without normalized telemetry can mask failures.
	- **Mitigation:** require WS2 instrumentation before broad WS3/WS4 cutovers.
- **Deprecation drift:** temporary compatibility paths can become permanent.
	- **Mitigation:** require every deprecation path to include owner + sunset date + removal issue/plan linkage.
- **Operational overload:** modernization work can compete with live operations.
	- **Mitigation:** cap concurrent high-risk workstreams and preserve rollback rehearsals.

## 12. Owner Confirmation and Decision Record

### 12.1 Decision Record (2026-02-12)

1. **Startup supervision default:** degraded mode is allowed for core subsystems when explicitly documented in subsystem runbooks.
2. **Telemetry retention baseline:** 60-day retention target for anonymous telemetry MVP.
3. **Community deprecation window:** minimum 8-week communication window before hard removals.
4. **Compatibility gate seed set:** seed rolling, daily challenge, and active tournament flows.

### 12.2 Follow-up Status

- Compatibility gate workflow set is now defined in section 7.1 and should be reused by all subordinate rollout plans.
