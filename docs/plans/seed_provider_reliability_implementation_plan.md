# Plan: Seed Provider Reliability Contract Implementation

> **Status:** Draft  
> **Last updated:** 2026-02-12  
> **Source design:** [Seed Provider Reliability Contract](../design/seed_provider_reliability_contract.md)

## Objective

Implement a single provider execution contract (timeouts, retries, normalized errors, audit parity) across Discord, RaceTime, and API without breaking existing generation flows.

## Scope

In scope:

- Shared provider execution wrapper
- Normalized exception taxonomy
- Shared success audit/failure log behavior
- Adapter migration for helper-only and class-based providers
- Surface cleanup of duplicated retry/error/audit logic

Out of scope:

- Provider business-rule redesign
- Non-generation command workflows

## Execution Phases

### Phase 1 — Contract Scaffolding

- Add shared wrapper enforcing 60s timeout and 3-attempt exponential retry.
- Add normalized exceptions and canonical provider response object.
- Add structured call-level observability fields.

### Phase 2 — Provider Adapter Migration

- Wrap helper-based providers behind contract adapters.
- Route class-based providers through the shared execution wrapper.
- Keep behavior-compatible outputs at all existing call sites.

### Phase 3 — Audit and Failure Semantics Unification

- Add shared success audit writer with provider metadata.
- Add structured failure logging with normalized error types.
- Enforce parity for all providers.

### Phase 4 — Surface Cleanup

- Remove duplicate retry/error/audit code from Discord, RaceTime, and API layers.
- Leave only presentation-layer message mapping in surfaces.

## Release Gates

1. **Behavior Gate:** existing generation success outputs preserved.
2. **Reliability Gate:** timeout/retry policy enforced for all provider calls.
3. **Audit Gate:** success parity and failure observability validated across providers.
4. **Rollback Gate:** staged rollout with reversible adapter switching.

## Concrete Checklist

- Implement wrapper + exception classes + canonical response.
- Migrate helper providers to adapters.
- Migrate class-backed providers to wrapper execution path.
- Integrate shared audit success writer and failure logs.
- Remove duplicated surface retry/error/audit logic.
- Validate Discord, RaceTime, and API generation flows.

## Success Criteria

- Every provider call uses the shared execution contract.
- Provider errors normalize consistently while preserving provider message content.
- Audit parity and failure observability are consistent across all surfaces.
