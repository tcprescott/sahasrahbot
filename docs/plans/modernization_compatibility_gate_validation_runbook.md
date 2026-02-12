# Plan: Modernization Compatibility Gate Validation Runbook

> **Status:** Draft  
> **Last updated:** 2026-02-12  
> **Governing source:** [Application Modernization Vision (2026–2027)](application_modernization_vision_2026_2027.md)

## Objective

Provide an executable, repeatable validation checklist for compatibility-gate evidence across the modernization workflow baseline.

## Scope

In scope:

- Workflow-level validation tasks
- Required evidence artifacts for gate reviews
- Rollback verification tasks per workflow
- Bi-weekly review packet structure

Out of scope:

- Implementing feature changes in runtime code
- Defining new compatibility workflows outside the umbrella plan baseline

## Baseline Workflows

This runbook executes the baseline set defined in [Application Modernization Vision (2026–2027)](application_modernization_vision_2026_2027.md#71-compatibility-gate-workflow-set-phase-a-baseline):

1. Discord seed rolling
2. RaceTime seed rolling
3. API seed generation endpoint
4. Discord daily challenge flow
5. Active tournament lifecycle flow
6. Tournament registry activation flow
7. Bot startup and command registration flow
8. Critical provider failure handling flow

## Execution Cadence

- **Primary cadence:** bi-weekly modernization checkpoint
- **Required rerun triggers:**
  - Before phase-exit gate review
  - After changes to provider wrappers, registry activation logic, startup lifecycle, or Discord cog loading
  - After rollback execution for any modernization change

## Evidence Packet Template (Required)

For each workflow, capture:

- **Result:** pass/fail
- **Timestamp:** UTC run time
- **Operator:** reviewer name/handle
- **Environment:** local/staging/production-like
- **Artifacts:** logs, screenshots, command output, API response traces
- **Rollback status:** not required / validated / executed
- **Notes:** regressions, degraded-mode behavior, and follow-up items

## Workflow Validation Checklists

### 1) Discord Seed Rolling

Validation tasks:

- Execute representative Discord seed-generation command for an active game/preset.
- Verify success response structure and user-visible error contract for one controlled failure case.
- Confirm generation audit success/failure records are written.

Evidence:

- Discord interaction output capture
- Provider/audit log lines for success and failure paths

Rollback check:

- Disable latest generation path change (flag/config/revert path) and confirm seed command remains operational.

### 2) RaceTime Seed Rolling

Validation tasks:

- Execute representative RaceTime room/handler seed-generation flow.
- Verify operator-visible outcome messaging and normalized failure behavior.
- Confirm provider metadata appears in structured logs.

Evidence:

- RaceTime bot output/log excerpts
- Provider reliability wrapper log traces

Rollback check:

- Revert adapter selection for changed provider path and re-run baseline room flow.

### 3) API Seed Generation Endpoint

Validation tasks:

- Call representative API seed endpoint used in production flow.
- Verify status code and response contract for success and normalized provider failure.
- Confirm API-layer logs contain workflow correlation details.

Evidence:

- Request/response captures (success + failure)
- API process logs with normalized error type

Rollback check:

- Switch API path to prior provider execution path and verify endpoint behavior remains contract-compatible.

### 4) Discord Daily Challenge Flow

Validation tasks:

- Trigger daily challenge generation/posting path (scheduled or controlled manual trigger).
- Verify posting destination and message contract.
- Confirm failure path logs are emitted and actionable.

Evidence:

- Posted daily challenge capture
- Scheduler/task logs for success and failure conditions

Rollback check:

- Disable latest daily-flow change and verify prior posting behavior remains functional.

### 5) Active Tournament Lifecycle Flow

Validation tasks:

- Execute active tournament lifecycle path: room creation/invite/roll/report.
- Verify active handlers operate without lifecycle regression.
- Confirm no unintended coupling regression from config/boundary changes.

Evidence:

- Tournament lifecycle event/log excerpts
- Handler execution traces for active tournament set

Rollback check:

- Restore previous handler activation path and verify active lifecycle remains intact.

### 6) Tournament Registry Activation Flow

Validation tasks:

- Validate configured seasonal activation profile loads at startup.
- Verify startup summary logs show source/profile/enabled handlers.
- Validate invalid configuration fails before operational loops begin.

Evidence:

- Startup logs showing selected source/profile
- Validation failure output for intentionally invalid config in non-production environment

Rollback check:

- Toggle fallback registry source and verify startup loads expected handler set.

### 7) Bot Startup and Command Registration Flow

Validation tasks:

- Start bot stack with current config and validate subsystem startup status.
- Verify expected command groups register and retired groups remain absent.
- Verify degraded-mode handling follows documented policy.

Evidence:

- Startup supervision/health logs
- Command sync/registration logs

Rollback check:

- Revert last startup/cog-load change and verify baseline startup + command registration.

### 8) Critical Provider Failure Handling Flow

Validation tasks:

- Induce controlled provider timeout/failure condition in safe environment.
- Verify timeout/retry policy execution and normalized error mapping.
- Verify operator-visible failure messaging remains actionable and uncaught exceptions do not escape.

Evidence:

- Retry/timeout log sequence
- Surface-level user/operator failure output

Rollback check:

- Switch to previous provider execution path and verify controlled failure remains handled.

## Gate Review Output Format

For each bi-weekly review, publish:

- Baseline workflow matrix (8 workflows, pass/fail)
- Open regressions with severity and owner
- Rollback readiness summary
- Recommendation: proceed / proceed-with-conditions / hold

## Completion Criteria

This runbook is considered operational when:

- All 8 workflows have at least one completed evidence packet.
- Evidence format is consistently used across at least two checkpoint cycles.
- Phase-gate reviews reference this runbook artifacts directly.
