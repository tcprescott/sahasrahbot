# Plan: Authlib Migration for Discord OAuth

> **Status:** Draft  
> **Last updated:** 2026-02-12  
> **Related umbrella plan:** [Application Modernization Vision (2026–2027)](application_modernization_vision_2026_2027.md)

## Objective

Migrate Discord OAuth in the web/API surface from `Quart-Discord` to `Authlib` with minimal migration risk, preserved login/session behavior, and explicit rollback controls.

## Why This Migration

- Reduce framework-specific auth coupling.
- Move to a broadly maintained OAuth client stack.
- Improve control over OAuth error handling, token lifecycle handling, and security hardening.

## Scope

In scope:

- OAuth client integration replacement in API auth path.
- Session/token handling parity with existing behavior.
- Failure/error mapping and observability updates for auth paths.
- Phased dual-path transition with fallback toggle.

Out of scope:

- User-facing auth flow redesign.
- Non-Discord identity provider expansion.
- Major template/UI changes.

## Risk Controls

- No irreversible cutover in a single release.
- Compatibility gate evidence required for API auth/login/logout paths.
- Feature-flag or runtime selector maintained during transition.
- Rollback instructions required before each cutover phase.

## Execution Phases

### Phase 0 — Discovery and Contract Definition

- Document current `Quart-Discord` behavior contract (login, callback, session, logout, token-expiry handling).
- Define Authlib target contract and parity requirements.
- Enumerate security requirements (redirect URI validation, secure cookie settings, secret requirements).

Exit criteria:

- Behavior contract matrix approved.
- Rollback strategy documented.

### Phase 1 — Authlib Scaffolding (No Traffic Switch)

- Add Authlib client wrapper module and configuration schema.
- Implement OAuth authorize/callback/token parsing paths behind a disabled switch.
- Add structured auth telemetry/error classification.

Exit criteria:

- New path compiles and runs in non-default mode.
- Observability fields emitted for auth success/failure.

### Phase 2 — Dual-Path Validation

- Enable Authlib path in controlled environment while keeping `Quart-Discord` fallback.
- Validate login/logout/session renewal behaviors and failure semantics.
- Validate callback/CSRF state handling and secret/session policy.

Exit criteria:

- Compatibility checks pass for API auth workflows.
- No unresolved critical regression from parity matrix.

### Phase 3 — Controlled Production Cutover

- Switch production default to Authlib path.
- Keep fallback selector for one stabilization window.
- Monitor auth failure rates and rollback readiness.

Exit criteria:

- Stabilization window completes with acceptable incident profile.
- Rollback path verified but not required.

### Phase 4 — Cleanup

- Remove `Quart-Discord` runtime usage and legacy auth glue code.
- Remove fallback selector and dead code.
- Finalize docs/context updates for architecture and tech stack.

Exit criteria:

- Legacy path fully removed.
- Documentation and runbooks updated.

## Release Gates

1. **Compatibility Gate:** login/callback/logout/session workflows preserve expected behavior contract.
2. **Security Gate:** no insecure OAuth transport in non-local runtime; strict secret/session validation enforced.
3. **Observability Gate:** auth success/failure/expiry outcomes are measurable and classified.
4. **Rollback Gate:** fallback path or release rollback procedure documented and tested per phase.

## Compatibility Workflow Coverage

This plan must provide evidence for these modernization baseline workflows:

- API seed generation endpoint (OAuth-protected usage context where applicable)
- Bot startup and command registration flow (indirectly unaffected by auth stack switch)

## Concrete Checklist

- Capture current `Quart-Discord` behavior matrix.
- Add Authlib integration module + configuration.
- Implement dual-path auth runtime selector.
- Add auth telemetry/error taxonomy events.
- Execute dual-path parity validation in controlled environment.
- Cut over production default to Authlib.
- Remove `Quart-Discord` runtime path after stabilization.

## Success Criteria

- Discord OAuth runs on Authlib with user-visible parity.
- Security posture improves (explicit secret/session/callback controls).
- Legacy auth dependency path is removed without major auth regressions.
