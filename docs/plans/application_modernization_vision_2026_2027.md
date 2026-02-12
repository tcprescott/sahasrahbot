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

## WS1 — Runtime Security Baseline (Priority: P0)

- Remove insecure OAuth transport from non-local runtime paths.
- Enforce non-empty app secret and startup validation checks.
- Complete secrets rotation/revocation workflow and documentation.
- Add security-focused config audit at startup (required/optional env keys).

## WS2 — Observability and Operations (Priority: P0)

- Implement shared anonymous telemetry MVP and retention policy.
- Standardize error taxonomy and provider failure classification.
- Add startup supervision strategy and subsystem health instrumentation.
- Publish operational dashboards/queries for daily reliability review.

## WS3 — Configuration and Boundary Hardening (Priority: P1)

- Deliver `GuildConfigService` migration and remove guild monkey-patching.
- Complete channel-name to channel-ID migration.
- Consolidate seasonal toggles into validated runtime config.
- Define clear ownership of config, cache, and persistence layers.

## WS4 — Legacy Surface Reduction (Priority: P1)

- Execute role-assignment deprecation/removal plan.
- Execute multiworld Discord deprecation/removal plan.
- Establish quarterly dead-weight review to retire inactive feature paths.
- Track removals with migration notes and rollback windows.

## WS5 — Developer Velocity Foundation (Priority: P2)

- Reconcile declared dependencies with runtime imports.
- Introduce minimum quality gates (lint + targeted smoke validation).
- Expand type coverage on cross-module interfaces first.
- Incrementally improve module-level testability for core flows.

## 6. Phased Roadmap

## Phase A (Q1–Q2 2026): Stabilize and Secure

- WS1 + WS2 baseline delivered.
- No net-new high-risk feature surface until security/observability gates pass.

## Phase B (Q2–Q3 2026): Boundaries and Config Migration

- WS3 delivered with compatibility windows and rollback plans.
- Tournament/config loader and seed-provider reliability wrappers operational.

## Phase C (Q3–Q4 2026): Legacy Reduction and Policy Simplification

- WS4 deprecations finalized; dead paths removed.
- Cross-surface behavior contracts documented and enforced.

## Phase D (2027): Performance and Optional Deployment Evolution

- Optimize hotspots using telemetry evidence.
- Re-evaluate process split feasibility only if module contracts are stable and operationally justified.

## 7. Decision Gates (Risk Controls)

Each phase/workstream must pass:

1. **Compatibility Gate:** Existing critical commands/workflows remain functional.
2. **Observability Gate:** New path emits measurable success/failure signals.
3. **Rollback Gate:** Documented rollback or feature-flag fallback exists.
4. **Security Gate:** No insecure defaults introduced or retained.

## 8. Success Metrics

- Startup failures become explicit, observable, and actionable (no silent subsystem degradation).
- Security posture: no insecure transport/default-empty-secret in non-local runtime.
- Coverage: top user-critical flows instrumented with normalized outcomes.
- Change safety: deprecations/removals executed with documented impact and low incident rate.
- Developer efficiency: reduced time-to-safely-change high-traffic modules.

## 9. Plan Relationships

This vision plan governs and sequences:

- [Discord Refactor](discord_refactor.md)
- [Anonymous Telemetry & User Stats Plan](anonymous_telemetry_user_stats_plan.md)
- [Seed Provider Reliability Contract Implementation](seed_provider_reliability_implementation_plan.md)
- [Tournament Registry Config-Driven Rollout](tournament_registry_config_rollout_plan.md)
- [Discord Role Assignment Deprecation & Removal](discord_role_assignment_deprecation_removal_plan.md)
- [Discord Multiworld Deprecation & Removal](discord_multiworld_deprecation_removal_plan.md)

Design references informing these plans:

- [Seed Provider Reliability Contract](../design/seed_provider_reliability_contract.md)
- [Tournament Registry Config-Driven Design](../design/tournament_registry_config_design.md)
- [Discord Role Assignment Deprecation Audit](../design/discord_role_assignment_deprecation_audit.md)
- [Discord Multiworld Deprecation Audit](../design/discord_multiworld_deprecation_audit.md)

## 10. Governance Cadence

- **Bi-weekly:** modernization checkpoint against risk, incident trends, and blocked migrations.
- **Monthly:** dead-weight review and deprecation scoreboard update.
- **Quarterly:** architecture checkpoint for modular boundary health and optional topology reassessment.
