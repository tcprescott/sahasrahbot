# Modernization Execution Tracker

> **Status:** Active  
> **Last updated:** 2026-02-12  
> **Governing plans:** [Modernization Meta Execution Plan (AI-Accelerated)](modernization_meta_execution_plan_ai_accelerated.md), [Application Modernization Vision (2026–2027)](application_modernization_vision_2026_2027.md)

## Purpose

This tracker provides a live view of modernization program status across all five workstreams (WS1–WS5), linking concrete plan deliverables to gate milestones and owners.

## Workstream Structure

### WS1: Runtime Security Baseline

**Priority:** Critical  
**Gate alignment:** A-gate (Phase 1 exit)

| Plan/Component | Owner | Status | Gate Milestone | Notes |
|----------------|-------|--------|----------------|-------|
| [Authlib Discord OAuth Migration](authlib_discord_oauth_migration_plan.md) | TBD | Not Started | A-gate: Phase 0/1 scaffolding | Auth stack migration scaffolding |
| Security hardening actions (vision doc) | TBD | Not Started | A-gate: Insecure defaults blocked | Runtime validation checks |
| Startup validation/supervision strategy | TBD | Not Started | A-gate: Fail-fast policy defined | Subsystem startup supervision |

**Exit criteria:**
- Security checks block insecure non-local defaults
- Rollback steps documented for each introduced flag/path

---

### WS2: Observability and Operations

**Priority:** Critical  
**Gate alignment:** A-gate (Phase 1 exit)

| Plan/Component | Owner | Status | Gate Milestone | Notes |
|----------------|-------|--------|----------------|-------|
| [Anonymous Telemetry & User Stats Plan](anonymous_telemetry_user_stats_plan.md) | TBD | Not Started | A-gate: Baseline telemetry active | Telemetry storage/service scaffolding |
| [Modernization Compatibility Gate Validation Runbook](modernization_compatibility_gate_validation_runbook.md) | TBD | Active | Phase 0: First evidence cycle | Bi-weekly gate review execution |

**Exit criteria:**
- Baseline telemetry emits success/failure for selected critical flows
- First checkpoint packet produced for at least 2 baseline workflows

---

### WS3: Configuration and Boundary Hardening

**Priority:** High  
**Gate alignment:** B-gate partial (Phase 2 exit)

| Plan/Component | Owner | Status | Gate Milestone | Notes |
|----------------|-------|--------|----------------|-------|
| [Discord Refactor](discord_refactor.md) | TBD | Not Started | B-gate: GuildConfigService pilot | Phase 2 guild config service migration |
| [Tournament Registry Config-Driven Rollout](tournament_registry_config_rollout_plan.md) | TBD | Not Started | B-gate: Config loader active | Config-backed tournament registry |
| [Seed Provider Reliability Contract Implementation](seed_provider_reliability_implementation_plan.md) | TBD | Not Started | B-gate: Provider wrapper active | Shared provider reliability contract |

**Exit criteria:**
- Provider reliability contract active on primary generation paths
- Config-backed tournament registry runs with explicit startup source logs
- Compatibility workflows 1, 2, 3, 6, 8 pass in staging evidence cycle

---

### WS4: Legacy Surface Reduction

**Priority:** Medium  
**Gate alignment:** C-gate trajectory (Phase 3 exit)

| Plan/Component | Owner | Status | Gate Milestone | Notes |
|----------------|-------|--------|----------------|-------|
| [Discord Role Assignment Deprecation & Removal](discord_role_assignment_deprecation_removal_plan.md) | TBD | Not Started | C-gate: Deprecation disablement | Role-assignment deprecation path |
| [Discord Multiworld Deprecation & Removal](discord_multiworld_deprecation_removal_plan.md) | TBD | Not Started | C-gate: Runtime removal | Multiworld command deprecation |
| Channel name-to-ID config migration | TBD | Not Started | C-gate: Compatibility guards active | Config boundary cleanup |

**Exit criteria:**
- Deprecated command surfaces removed from runtime registration
- Non-role/non-multiworld command groups validated unaffected
- Data cleanup plan approved with rollback decision point

---

### WS5: Developer Velocity Foundation

**Priority:** Medium  
**Gate alignment:** Phase 4+ (sustainment mode)

| Plan/Component | Owner | Status | Gate Milestone | Notes |
|----------------|-------|--------|----------------|-------|
| Dependency declaration guard + CI integration | TBD | Not Started | Phase 4: CI enforcement active | CI gate enforcement |
| Modular boundary tightening | TBD | Not Started | Phase 4: Ongoing | Testability improvements |
| Repeatable bi-weekly compatibility cycle | TBD | In Progress | Phase 0: First evidence cycle | Gate pass rate tracking |

**Exit criteria:**
- Gate pass rate and rollback readiness become routine release quality metrics
- Remaining modernization backlog prioritized by measured risk/impact

---

## Phase Milestones

### Phase 0: Program Bootstrap (Week 0–1)

**Status:** In Progress

**Deliverables:**
- [x] Program board with WS1–WS5 epics and gate-linked milestones
- [x] Standardized gate evidence template
- [x] Feature-flag inventory for dual-path migrations
- [ ] AI task templates for audits, migrations, and validation packets
- [ ] First checkpoint packet produced for at least 2 baseline workflows
- [ ] Owners assigned for delivery, validation, and rollback decisions

---

### Phase 1: Security + Signal Baseline (Week 1–4)

**Status:** Not Started

**Primary focus:**
- Auth stack migration scaffolding (Phase 0/1 of Authlib plan)
- Startup validation/supervision strategy definition
- Telemetry storage/service scaffolding and normalized error taxonomy

**Exit criteria (A-gate aligned):**
- Security checks block insecure non-local defaults
- Baseline telemetry emits success/failure for selected critical flows
- Rollback steps documented for each introduced flag/path

---

### Phase 2: Contract Migrations (Week 4–8)

**Status:** Not Started

**Primary focus:**
- Seed provider wrapper/adapters in Discord, RaceTime, and API paths
- Tournament config loader + dual-path runtime switch
- Guild config service pilot in one cog (`daily`) before broad migration

**Exit criteria (B-gate partial):**
- Provider reliability contract active on primary generation paths
- Config-backed tournament registry runs with explicit startup source logs
- Compatibility workflows 1, 2, 3, 6, 8 pass in staging evidence cycle

---

### Phase 3: Deprecation Execution (Week 8–12)

**Status:** Not Started

**Primary focus:**
- Role-assignment deprecation disablement path
- Multiworld command deprecation and runtime removal path
- Begin channel name-to-ID config migration with compatibility guards

**Exit criteria (C-gate trajectory):**
- Deprecated command surfaces removed from runtime registration
- Non-role/non-multiworld command groups validated unaffected
- Data cleanup plan approved with rollback decision point

---

### Phase 4: Velocity and Sustainment (Week 12+)

**Status:** Not Started

**Primary focus:**
- CI gate enforcement for dependency declarations and targeted smoke checks
- Ongoing modular boundary tightening and testability improvements
- Repeatable bi-weekly compatibility cycle with trend reporting

**Exit criteria:**
- Gate pass rate and rollback readiness become routine release quality metrics
- Remaining modernization backlog prioritized by measured risk/impact

---

## 30/60/90-Day Targets

### First 30 Days (Target Date: TBD)
- [ ] Authlib dual-path scaffolding merged behind selector
- [ ] Telemetry table/service and minimal instrumentation merged
- [ ] Compatibility runbook executed for first full 8-workflow baseline packet

### First 60 Days (Target Date: TBD)
- [ ] Shared provider wrapper adopted in primary generation entrypoints
- [ ] Tournament registry config path enabled in controlled environment
- [ ] GuildConfigService proven in pilot cog and migration playbook finalized

### First 90 Days (Target Date: TBD)
- [ ] Deprecation phases for role and multiworld reach functional disablement
- [ ] Channel ID migration path started with validation tooling
- [ ] Compatibility evidence cycles stable enough to govern phase progression

---

## Compatibility Gate Status

**Last gate review:** Not yet executed  
**Next scheduled gate review:** TBD (bi-weekly cadence)

### Baseline Workflow Matrix (8 workflows)

| # | Workflow | Last Result | Last Evidence Date | Owner | Notes |
|---|----------|-------------|-------------------|-------|-------|
| 1 | Discord seed rolling | Not Tested | — | TBD | — |
| 2 | RaceTime seed rolling | Not Tested | — | TBD | — |
| 3 | API seed generation endpoint | Not Tested | — | TBD | — |
| 4 | Discord daily challenge flow | Not Tested | — | TBD | — |
| 5 | Active tournament lifecycle flow | Not Tested | — | TBD | — |
| 6 | Tournament registry activation flow | Not Tested | — | TBD | — |
| 7 | Bot startup and command registration flow | Not Tested | — | TBD | — |
| 8 | Critical provider failure handling flow | Not Tested | — | TBD | — |

---

## Active Regressions

_No regressions currently tracked._

---

## Rollback Readiness Summary

| Workstream | Rollback Status | Last Validation | Notes |
|------------|----------------|-----------------|-------|
| WS1 | N/A | — | No changes deployed |
| WS2 | N/A | — | No changes deployed |
| WS3 | N/A | — | No changes deployed |
| WS4 | N/A | — | No changes deployed |
| WS5 | N/A | — | No changes deployed |

---

## Program Governance

### Cadence
- **Daily async check:** Delivery/validation blockers and risk changes
- **Weekly planning:** Select next small-batch change set by gate readiness
- **Bi-weekly gate review:** Run full compatibility matrix and publish recommendation
- **Monthly architecture checkpoint:** Verify boundary drift, dual-path debt, and sunset status

### Required Artifacts per Bi-Weekly Review
- Workflow pass/fail matrix (8 baseline workflows)
- Regression list with owner + target date
- Rollback readiness summary per active workstream
- Sunset ledger for all temporary compatibility paths

### Risk Budget and Concurrency Limits
- Maximum 2 concurrent high-risk migrations (WS1/WS3/WS4 class) at once
- Maximum 1 destructive schema change window active at a time
- No net-new deprecation removal starts during unresolved critical regression windows

---

## Immediate Next Actions

1. Define owners for delivery, validation, and rollback per workstream
2. Run first compatibility evidence cycle using the existing runbook
3. Create AI task templates for audits, migrations, and validation packets
4. Start Phase 1 with three bounded implementation slices:
   - Authlib scaffolding (no traffic switch)
   - Telemetry service/table scaffolding
   - Startup security validation checks
