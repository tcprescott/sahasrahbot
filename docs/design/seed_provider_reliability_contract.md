# Seed Provider Reliability Contract

> Last updated: 2026-02-12  
> Scope: All seed-generation providers used by Discord, RaceTime, and API entrypoints

## Purpose

Define one implementation contract for provider execution behavior so all seed sources have consistent reliability, auditing, and failure semantics.

## Confirmed Policy Defaults

Owner-confirmed defaults for this contract:

- Request timeout default: 60 seconds per outbound provider call.
- Retry baseline: 3 attempts with exponential backoff.
- Audit parity: mandatory for all providers, including helper-only providers.
- User-facing errors: expose provider message directly.

## Contract Requirements

## 1) Execution Envelope

Every seed provider call runs inside a shared execution wrapper that enforces:

- Timeout: 60 seconds per attempt.
- Retries: 3 total attempts.
- Backoff: exponential delay sequence `1s`, `2s` between retries.
- Retryable classes:
  - network timeouts
  - connection reset / DNS / temporary transport errors
  - HTTP 429
  - HTTP 5xx
- Non-retryable classes:
  - validation/input errors
  - HTTP 4xx excluding 429
  - schema/parsing errors caused by local payload construction

## 2) Error Semantics

All providers normalize failures into contract-level exceptions while preserving provider detail.

Required exception taxonomy:

- `SeedProviderTimeoutError`
- `SeedProviderUnavailableError`
- `SeedProviderRateLimitError`
- `SeedProviderInvalidRequestError`
- `SeedProviderResponseFormatError`

Required fields on normalized exceptions:

- `provider`
- `operation`
- `attempts`
- `status_code` (if available)
- `provider_message`

User messaging rule:

- Return provider message directly when available, prefixed by provider name for context.

## 3) Audit Parity Contract

Every successful generation path writes a unified audit record, regardless of provider implementation style.

Minimum required audit payload:

- `randomizer`
- `gentype`
- `genoption`
- `permalink`
- `hash_id` (nullable if provider has no hash)
- `settings` (raw effective settings payload)
- provider metadata:
  - `provider`
  - `operation`
  - `attempt_count`
  - `latency_ms`
  - `surface` (`discord`, `racetime`, `api`)

Failure audit policy:

- Emit structured failure log event with same metadata plus normalized error type.
- Do not write successful-generation DB audit row for failed generations.

## 4) Provider Interface

All providers must be invokable through a common interface boundary, whether class-backed or helper-backed.

Required conceptual interface:

- input: canonical generation request (`preset/settings`, race/spoiler flags, branch, extra options)
- output: canonical generation response (`url`, `hash_or_id`, `code`, `provider_meta`)
- failure: normalized exceptions only

Design constraint:

- Helper-only providers are wrapped by adapter classes so they comply with audit and error contracts.

## 5) Surface Integration Rules

Discord, RaceTime, and API layers must:

- call providers through the shared execution contract only
- avoid provider-specific retry logic in surface code
- avoid provider-specific audit writes in surface code
- map normalized exceptions to user-visible messages consistently

## 6) Observability Requirements

Required structured logs for each provider call:

- `provider`
- `operation`
- `surface`
- `attempt`
- `duration_ms`
- `outcome` (`success`, `retry`, `failure`)
- `error_type` (on failure)

Optional correlation field (recommended):

- `generation_request_id` propagated from entrypoint to provider wrapper.

## Reference Mapping to Current Code

Current generation touchpoints to migrate behind this contract:

- `alttprbot/alttprgen/generator.py`
- `alttprbot/alttprgen/spoilers.py`
- `alttprbot/alttprgen/smz3multi.py`
- `alttprbot/alttprgen/randomizer/smdash.py`
- `alttprbot/alttprgen/randomizer/ctjets.py`
- `alttprbot/alttprgen/randomizer/avianart.py`
- `alttprbot_discord/cogs/generator.py`
- `alttprbot_racetime/handlers/alttpr.py`
- `alttprbot_racetime/handlers/smr.py`
- `alttprbot_racetime/handlers/smz3.py`
- `alttprbot_api/blueprints/sglive.py`

## Migration Plan

### Phase 1: Contract scaffolding

- Add shared provider execution wrapper module.
- Add normalized exception classes.
- Add canonical response object.

### Phase 2: Provider adapters

- Wrap helper-based providers (DASH, CTJets, AVIANART) in contract adapters.
- Migrate class-based providers to route through shared wrapper for timeout/retry behavior.

### Phase 3: Audit unification

- Add shared audit writer invoked by wrapper on success.
- Add structured failure logs for all provider failures.

### Phase 4: Surface cleanup

- Remove duplicate retry/error/audit logic from Discord, RaceTime, and API layers.
- Keep only presentation-level message mapping in surfaces.

## Acceptance Criteria

- All provider calls enforce 60-second timeout and 3-attempt exponential retry policy.
- All seed providers, including helper-only providers, emit parity audit records on success.
- All provider failures surface normalized exception types.
- Discord, RaceTime, and API entrypoints use only contract-wrapped provider calls.
- User-facing errors preserve direct provider message content when available.

## Open Design Choice

- Whether to store provider failure events in DB (new failure-audit table) or logs-only in first iteration.