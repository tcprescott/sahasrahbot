# Compatibility Evidence Packet Template

> **Purpose:** Standardized format for capturing compatibility workflow validation evidence  
> **Governing runbook:** [Modernization Compatibility Gate Validation Runbook](../plans/modernization_compatibility_gate_validation_runbook.md)  
> **Last updated:** 2026-02-12

## Usage

This template should be used for each workflow validation during:
- Bi-weekly modernization checkpoint reviews
- Before phase-exit gate reviews
- After changes to provider wrappers, registry activation logic, startup lifecycle, or Discord cog loading
- After rollback execution for any modernization change

Copy this template for each workflow validation and fill in all required fields.

---

## Evidence Packet

### Metadata

- **Workflow ID:** [1-8, or workflow name]
- **Workflow Name:** [e.g., "Discord seed rolling", "RaceTime seed rolling"]
- **Result:** [PASS / FAIL / DEGRADED]
- **Timestamp (UTC):** [YYYY-MM-DD HH:MM:SS UTC]
- **Operator:** [reviewer name/handle]
- **Environment:** [local / staging / production-like / other]
- **Validation Type:** [bi-weekly checkpoint / phase-exit gate / post-change / post-rollback]
- **Related Changes:** [PR numbers, commit SHAs, or "baseline validation"]

---

### Validation Tasks

List each validation task executed per the runbook checklist for this workflow:

- [ ] Task 1 description
- [ ] Task 2 description
- [ ] Task 3 description

**Task Execution Notes:**
[Describe any deviations from standard execution, environmental constraints, or notable conditions]

---

### Evidence Artifacts

#### Success Path Evidence

**Description:** [What success case was validated]

**Artifacts:**
- [Link or attach: logs, screenshots, command output, API response traces]
- [Additional artifact description]

**Key Observations:**
- [Notable success indicators]
- [Performance/timing observations if relevant]

---

#### Failure Path Evidence (if applicable)

**Description:** [What failure case was validated]

**Artifacts:**
- [Link or attach: error logs, failure output, exception traces]
- [Additional artifact description]

**Key Observations:**
- [Error handling behavior]
- [User-visible error messaging quality]
- [Normalized error type/code if applicable]

---

### Regression Analysis

**New Regressions Identified:** [YES / NO]

If YES, list:

1. **Regression:** [Brief description]
   - **Severity:** [Critical / High / Medium / Low]
   - **Impact:** [What is broken or degraded]
   - **Owner:** [Assigned to]
   - **Target Resolution Date:** [YYYY-MM-DD]
   - **Tracking:** [Issue/ticket number]

2. **Regression:** [Additional regressions]

---

### Rollback Verification

**Rollback Status:** [Not Required / Validated / Executed]

**Rollback Method:** [Flag toggle / Config revert / Code revert / Other]

**Rollback Validation:**
- [ ] Rollback procedure executed successfully
- [ ] Post-rollback functionality confirmed operational
- [ ] Rollback documented in runbook/tracker

**Rollback Notes:**
[Details on rollback execution, validation results, lessons learned]

---

### Follow-Up Items

List any action items, tech debt, or clarifications needed:

1. [Action item description] — Owner: [name], Target: [date]
2. [Additional items]

---

### Gate Recommendation

**Recommendation for this workflow:** [PROCEED / PROCEED WITH CONDITIONS / HOLD]

**Rationale:**
[Brief explanation of recommendation based on evidence]

**Conditions (if applicable):**
- [Condition 1 that must be met before proceeding]
- [Condition 2]

---

## Example Evidence Packet

Below is a filled example for reference:

---

### Metadata

- **Workflow ID:** 1
- **Workflow Name:** Discord seed rolling
- **Result:** PASS
- **Timestamp (UTC):** 2026-02-12 14:30:00 UTC
- **Operator:** @example-reviewer
- **Environment:** staging
- **Validation Type:** bi-weekly checkpoint
- **Related Changes:** baseline validation

---

### Validation Tasks

- [x] Execute representative Discord seed-generation command for an active game/preset
- [x] Verify success response structure and user-visible error contract for one controlled failure case
- [x] Confirm generation audit success/failure records are written

**Task Execution Notes:**
Executed seed generation for ALTTPR Standard preset in staging Discord server. Simulated provider timeout by temporarily modifying timeout threshold to trigger controlled failure.

---

### Evidence Artifacts

#### Success Path Evidence

**Description:** ALTTPR Standard seed generation via Discord slash command

**Artifacts:**
- Screenshot: discord_seed_success_2026-02-12.png
- Log excerpt:
  ```
  2026-02-12 14:28:15 UTC [INFO] seed_generator: Starting seed generation for preset=standard, user=12345
  2026-02-12 14:28:16 UTC [INFO] provider_wrapper: Provider=alttpr.com, timeout=60s, attempt=1/3
  2026-02-12 14:28:18 UTC [INFO] provider_wrapper: Success, seed=abc123, generation_time=2.1s
  2026-02-12 14:28:18 UTC [INFO] audit_logger: Logged seed generation success, audit_id=789
  ```

**Key Observations:**
- Seed generation completed in 2.1 seconds
- Discord interaction showed seed URL and permalink correctly
- Audit record written with success status

---

#### Failure Path Evidence

**Description:** Controlled provider timeout

**Artifacts:**
- Log excerpt:
  ```
  2026-02-12 14:29:30 UTC [INFO] provider_wrapper: Provider=alttpr.com, timeout=5s, attempt=1/3
  2026-02-12 14:29:35 UTC [WARN] provider_wrapper: Timeout on attempt 1, retrying...
  2026-02-12 14:29:35 UTC [INFO] provider_wrapper: Provider=alttpr.com, timeout=5s, attempt=2/3
  2026-02-12 14:29:40 UTC [WARN] provider_wrapper: Timeout on attempt 2, retrying...
  2026-02-12 14:29:40 UTC [INFO] provider_wrapper: Provider=alttpr.com, timeout=5s, attempt=3/3
  2026-02-12 14:29:45 UTC [ERROR] provider_wrapper: All attempts exhausted, normalized_error=PROVIDER_TIMEOUT
  2026-02-12 14:29:45 UTC [INFO] audit_logger: Logged seed generation failure, audit_id=790, error_type=PROVIDER_TIMEOUT
  ```
- Screenshot: discord_seed_failure_2026-02-12.png

**Key Observations:**
- Retry policy executed correctly (3 attempts with 5s timeout each)
- User-visible error message was actionable: "Seed generation timed out. Please try again later."
- Audit record written with failure status and normalized error type

---

### Regression Analysis

**New Regressions Identified:** NO

---

### Rollback Verification

**Rollback Status:** Not Required (baseline validation)

**Rollback Method:** N/A

**Rollback Validation:**
- N/A

**Rollback Notes:**
N/A — This is a baseline validation with no recent changes to roll back.

---

### Follow-Up Items

1. Consider reducing timeout threshold for faster failure feedback in non-critical flows — Owner: @dev-team, Target: 2026-03-01
2. Add provider selection telemetry to track which provider is being used — Owner: @telemetry-owner, Target: 2026-03-15

---

### Gate Recommendation

**Recommendation for this workflow:** PROCEED

**Rationale:**
Workflow passed both success and controlled failure paths. Audit logging working correctly, retry policy executed as expected, user-facing errors are actionable.

**Conditions (if applicable):**
N/A
