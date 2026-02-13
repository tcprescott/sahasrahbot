# Feature Flag Inventory

> **Status:** Active  
> **Last updated:** 2026-02-12  
> **Governing principle:** All dual-path feature flags require owner + sunset date  
> **Related:** [Modernization Meta Execution Plan](../plans/modernization_meta_execution_plan_ai_accelerated.md)

## Purpose

This inventory tracks all feature flags used for dual-path migrations during modernization. Every flag must have a defined owner and a target sunset date to prevent indefinite technical debt accumulation.

## Control Mechanisms

Per the modernization meta execution plan:

- **Two-key release rule:** One delivery owner + one validation owner sign each gate packet
- **Sunset enforcement:** Every dual-path feature flag includes owner and target removal date
- **Concurrency limits:** Maximum 2 concurrent high-risk migrations (WS1/WS3/WS4 class) at once

## Flag Status Definitions

- **Proposed:** Flag planned but not yet implemented
- **Active:** Flag implemented and in use (dual-path active)
- **Deprecated:** Target path validated, old path retained for rollback only
- **Sunset:** Flag and old path removed from codebase
- **Abandoned:** Flag no longer needed (change reverted or superseded)

---

## Active Feature Flags

| Flag Name | Component | Owner | Validation Owner | Introduced | Target Sunset | Status | Workstream | Notes |
|-----------|-----------|-------|------------------|------------|---------------|--------|------------|-------|
| _No active flags yet_ | — | — | — | — | — | — | — | — |

---

## Proposed Feature Flags

| Flag Name | Component | Owner | Validation Owner | Target Introduction | Target Sunset | Status | Workstream | Notes |
|-----------|-----------|-------|------------------|---------------------|---------------|--------|------------|-------|
| `USE_AUTHLIB_OAUTH` | Discord OAuth | TBD | TBD | Phase 1 (Week 1-4) | Phase 2 (Week 8) | Proposed | WS1 | Auth stack migration selector |
| `USE_CONFIG_TOURNAMENT_REGISTRY` | Tournament Registry | TBD | TBD | Phase 2 (Week 4-8) | Phase 3 (Week 12) | Proposed | WS3 | YAML-backed tournament activation |
| `USE_PROVIDER_RELIABILITY_WRAPPER` | Seed Generation | TBD | TBD | Phase 2 (Week 4-8) | Phase 3 (Week 12) | Proposed | WS3 | Shared provider timeout/retry/error contract |
| `USE_GUILD_CONFIG_SERVICE` | Discord Guild Config | TBD | TBD | Phase 2 (Week 4-8) | Phase 4 (Week 16+) | Proposed | WS3 | Replace monkey-patching pattern |
| `ENABLE_ROLE_ASSIGNMENT_COMMANDS` | Discord Role Assignment | TBD | TBD | Current | Phase 3 (Week 12) | Proposed | WS4 | Deprecation control for reaction/voice roles |
| `ENABLE_MULTIWORLD_COMMANDS` | Discord Multiworld | TBD | TBD | Current | Phase 3 (Week 12) | Proposed | WS4 | Deprecation control for multiworld commands |

---

## Deprecated Feature Flags

_Flags in this section have been validated but retained for rollback capability._

| Flag Name | Component | Owner | Validation Owner | Deprecated Date | Target Sunset | Workstream | Notes |
|-----------|-----------|-------|------------------|-----------------|---------------|------------|-------|
| _No deprecated flags yet_ | — | — | — | — | — | — | — |

---

## Sunset Feature Flags (Historical)

_Flags in this section have been fully removed from the codebase._

| Flag Name | Component | Owner | Introduced | Sunset Date | Workstream | Notes |
|-----------|-----------|-------|------------|-------------|------------|-------|
| _No sunset flags yet_ | — | — | — | — | — | — |

---

## Abandoned Feature Flags (Historical)

_Flags that were planned but never activated, or activated then reverted._

| Flag Name | Component | Owner | Status Date | Workstream | Reason |
|-----------|-----------|-------|-------------|------------|--------|
| _No abandoned flags yet_ | — | — | — | — | — |

---

## Flag Implementation Guidelines

### Creating a New Feature Flag

1. **Propose:** Add to "Proposed Feature Flags" section with all required metadata
2. **Review:** Ensure owner + validation owner assigned and sunset date defined
3. **Implement:** Add flag to codebase with documentation in code and this inventory
4. **Activate:** Move to "Active Feature Flags" section when dual-path is live
5. **Update:** Keep status current in bi-weekly gate reviews

### Deprecating a Feature Flag

1. **Validate:** Confirm new path passes all relevant compatibility workflows
2. **Document:** Capture rollback steps and validation evidence
3. **Deprecate:** Move to "Deprecated Feature Flags" section
4. **Retain:** Keep deprecated path available for at least one gate review cycle
5. **Communicate:** Announce deprecation status to relevant stakeholders

### Sunsetting a Feature Flag

1. **Confirm:** Ensure no rollback needed for at least 2 gate review cycles
2. **Remove:** Delete flag and old path from codebase
3. **Archive:** Move to "Sunset Feature Flags" section with removal date
4. **Verify:** Confirm no references remain in code or documentation

### Abandoning a Feature Flag

1. **Decide:** Determine flag is no longer needed (change reverted or superseded)
2. **Clean:** Remove any implemented flag code
3. **Archive:** Move to "Abandoned Feature Flags" section with reason
4. **Communicate:** Document decision rationale for future reference

---

## Flag Audit Requirements

### Weekly
- Verify active flags have valid owners assigned
- Confirm no flags are blocking concurrent high-risk migrations

### Bi-Weekly (Gate Review)
- Review all active flags for sunset readiness
- Update status based on compatibility workflow results
- Escalate any flags approaching/past sunset date without decision

### Monthly (Architecture Checkpoint)
- Verify dual-path debt is decreasing over time
- Review abandoned/sunset flags for lessons learned
- Update sunset targets based on program velocity

---

## Risk Indicators

**High-risk situations that require escalation:**

1. Active flag count exceeds concurrency limits (>2 high-risk WS1/WS3/WS4 flags)
2. Any flag exceeds 90 days past target sunset date
3. Flag owner or validation owner becomes unavailable with no successor
4. Deprecated flag requires rollback activation after 2+ gate review cycles
5. Multiple flags in same component/subsystem (coupling risk)

---

## Contact and Governance

**Inventory maintainer:** TBD  
**Update cadence:** Bi-weekly gate reviews (minimum)  
**Escalation path:** TBD  
**Audit log:** All inventory updates should be committed to version control with descriptive commit messages
