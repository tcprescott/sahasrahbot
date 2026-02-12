# Plan: Modernization Meta Execution Plan (AI-Accelerated)

> **Status:** Draft  
> **Last updated:** 2026-02-12  
> **Planning horizon:** First 2 quarters of execution kickoff  
> **Governing roadmap:** [Application Modernization Vision (2026–2027)](application_modernization_vision_2026_2027.md)

## 1. Purpose

Convert the existing modernization strategy and component plans into an execution engine that can run in parallel with AI assistance while preserving migration safety.

This plan does not replace subordinate plans. It defines how to run them together, how to stage risk, and how to generate gate evidence continuously.

## 2. Execution Model

## 2.1 Program Structure

Use three lanes that run concurrently:

1. **Delivery Lane (code changes):** implements WS1–WS5 scoped tasks.
2. **Validation Lane (gates/evidence):** executes compatibility workflows and rollback checks on every increment.
3. **Documentation Lane (contracts/context):** keeps plans, runbooks, and context files synchronized with real state.

## 2.2 AI Acceleration Policy

AI is used for:

- Batch codebase analysis and coupling detection.
- Generating first-draft refactors behind explicit acceptance criteria.
- Creating migration checklists and operational runbooks from code deltas.
- Producing evidence packet drafts from logs/test output.

AI is not used as sole authority for:

- Security gate sign-off.
- Destructive schema operations without human-reviewed rollback steps.
- Final intent rationale for business-policy decisions unless owner-confirmed.

## 2.3 Control Mechanisms

- **Change unit size:** keep each implementation unit small enough to validate against a subset of the 8 baseline workflows.
- **Two-key release rule:** one delivery owner + one validation owner sign each gate packet.
- **Sunset enforcement:** every dual-path feature flag includes owner and target removal date.

## 3. Workstream Composition (Kickoff)

## 3.1 Priority Stack

Execution order follows risk-first constraints from the umbrella plan:

1. **WS1 Runtime Security Baseline**
2. **WS2 Observability and Operations**
3. **WS3 Configuration and Boundary Hardening**
4. **WS4 Legacy Surface Reduction**
5. **WS5 Developer Velocity Foundation**

## 3.2 Plan-to-Workstream Mapping

- WS1:
  - [Authlib Migration for Discord OAuth](authlib_discord_oauth_migration_plan.md)
  - Security hardening actions from [Application Modernization Vision (2026–2027)](application_modernization_vision_2026_2027.md)
- WS2:
  - [Anonymous Telemetry & User Stats Plan](anonymous_telemetry_user_stats_plan.md)
  - [Modernization Compatibility Gate Validation Runbook](modernization_compatibility_gate_validation_runbook.md)
- WS3:
  - [Discord Refactor](discord_refactor.md)
  - [Tournament Registry Config-Driven Rollout](tournament_registry_config_rollout_plan.md)
  - [Seed Provider Reliability Contract Implementation](seed_provider_reliability_implementation_plan.md)
- WS4:
  - [Discord Role Assignment Deprecation & Removal](discord_role_assignment_deprecation_removal_plan.md)
  - [Discord Multiworld Deprecation & Removal](discord_multiworld_deprecation_removal_plan.md)
- WS5:
  - Dependency declaration guard + CI integration tracked in `docs/context/active_state.md`

## 4. Phased Kickoff Plan

## Phase 0 (Week 0–1): Program Bootstrap

Goal:

- Establish delivery mechanics before high-risk code migrations.

Deliverables:

- Program board with WS1–WS5 epics and gate-linked milestones.
- Standardized gate evidence template (reusing compatibility runbook format).
- Feature-flag inventory for dual-path migrations.
- AI task templates for audits, migrations, and validation packets.

Exit criteria:

- First checkpoint packet produced for at least 2 baseline workflows.
- Owners assigned for delivery, validation, and rollback decisions.

## Phase 1 (Week 1–4): Security + Signal Baseline

Goal:

- Reduce critical runtime risk and make failures measurable.

Primary focus:

- Auth stack migration scaffolding (Phase 0/1 of Authlib plan).
- Startup validation/supervision strategy definition.
- Telemetry storage/service scaffolding and normalized error taxonomy.

AI acceleration opportunities:

- Static scan for insecure runtime defaults and empty-secret paths.
- Drafting auth parity matrix from existing OAuth routes.
- Generating telemetry instrumentation TODOs per surface boundary.

Exit criteria (A-gate aligned):

- Security checks block insecure non-local defaults.
- Baseline telemetry emits success/failure for selected critical flows.
- Rollback steps documented for each introduced flag/path.

## Phase 2 (Week 4–8): Contract Migrations (High Leverage)

Goal:

- Migrate shared contracts that reduce cross-surface drift.

Primary focus:

- Seed provider wrapper/adapters in Discord, RaceTime, and API paths.
- Tournament config loader + dual-path runtime switch.
- Guild config service pilot in one cog (`daily`) before broad migration.

AI acceleration opportunities:

- Auto-generate provider adapter stubs and exception mapping table.
- Detect duplicated retry/error/audit logic across surfaces.
- Produce YAML/profile validation fixtures and failure cases.

Exit criteria (B-gate partial):

- Provider reliability contract active on primary generation paths.
- Config-backed tournament registry runs with explicit startup source logs.
- Compatibility workflows 1, 2, 3, 6, 8 pass in staging evidence cycle.

## Phase 3 (Week 8–12): Deprecation Execution + Boundary Cleanup

Goal:

- Remove low-value legacy surfaces while preserving critical flows.

Primary focus:

- Role-assignment deprecation disablement path.
- Multiworld command deprecation and runtime removal path.
- Begin channel name-to-ID config migration with compatibility guards.

AI acceleration opportunities:

- Enumerate command references and dead-path dependencies.
- Generate migration scripts and dry-run reports for model/table cleanup.
- Produce deprecation comms draft from plan templates.

Exit criteria (C-gate trajectory):

- Deprecated command surfaces removed from runtime registration.
- Non-role/non-multiworld command groups validated unaffected.
- Data cleanup plan approved with rollback decision point before destructive migration.

## Phase 4 (Week 12+): Velocity and Sustainment

Goal:

- Convert modernization from project mode to standard operating mode.

Primary focus:

- CI gate enforcement for dependency declarations and targeted smoke checks.
- Ongoing modular boundary tightening and testability improvements.
- Repeatable bi-weekly compatibility cycle with trend reporting.

Exit criteria:

- Gate pass rate and rollback readiness become routine release quality metrics.
- Remaining modernization backlog prioritized by measured risk/impact.

## 5. First 30/60/90-Day Deliverable Matrix

## First 30 Days

- Authlib dual-path scaffolding merged behind selector.
- Telemetry table/service and minimal instrumentation merged.
- Compatibility runbook executed for first full 8-workflow baseline packet.

## First 60 Days

- Shared provider wrapper adopted in primary generation entrypoints.
- Tournament registry config path enabled in controlled environment.
- GuildConfigService proven in pilot cog and migration playbook finalized.

## First 90 Days

- Deprecation phases for role and multiworld reach functional disablement.
- Channel ID migration path started with validation tooling.
- Compatibility evidence cycles stable enough to govern phase progression.

## 6. Program Cadence and Governance

- **Daily async check:** delivery/validation blockers and risk changes.
- **Weekly planning:** select next small-batch change set by gate readiness.
- **Bi-weekly gate review:** run full compatibility matrix and publish recommendation.
- **Monthly architecture checkpoint:** verify boundary drift, dual-path debt, and sunset status.

Required artifacts per bi-weekly review:

- Workflow pass/fail matrix (8 baseline workflows).
- Regression list with owner + target date.
- Rollback readiness summary per active workstream.
- Sunset ledger for all temporary compatibility paths.

## 7. AI Operating Guardrails

- Every AI-generated change must map to one explicit checklist item in a plan doc.
- Every AI-generated migration script must include dry-run mode and validation output.
- AI-produced documentation that explains policy intent must use owner-confirmed rationale only.
- AI evidence synthesis is acceptable; gate decision remains human-owned.

## 8. Risk Budget and Concurrency Limits

To avoid operational overload:

- Maximum 2 concurrent high-risk migrations (WS1/WS3/WS4 class) at once.
- Maximum 1 destructive schema change window active at a time.
- No net-new deprecation removal starts during unresolved critical regression windows.

## 9. Immediate Next Actions (Week 0)

1. Create execution tracker issues from each subordinate plan’s concrete checklist.
2. Define owners for delivery, validation, and rollback per workstream.
3. Run first compatibility evidence cycle using the existing runbook.
4. Start Phase 1 with three bounded implementation slices:
   - Authlib scaffolding (no traffic switch)
   - telemetry service/table scaffolding
   - startup security validation checks

## 10. Success Definition for This Meta Plan

This meta plan is successful when:

- Modernization work is continuously shippable in small, validated increments.
- Compatibility evidence is available before decisions, not after incidents.
- AI increases throughput without weakening security, rollback readiness, or policy correctness.
