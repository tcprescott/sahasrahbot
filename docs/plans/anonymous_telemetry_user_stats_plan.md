# Plan: Anonymous Telemetry & Feature Usage Statistics

> **Status:** Draft  
> **Last updated:** 2026-02-12  
> **Goal:** Collect anonymous, low-risk product telemetry to identify feature usage across Discord, RaceTime, and Web/API surfaces.

## 1. Objective and Non-Goals

### Objective

Implement a shared telemetry pipeline that answers:

- Which features are being used most often?
- Which surfaces are active (Discord vs RaceTime vs API)?
- Where are failures concentrated by feature/provider?

### Non-Goals

- No content analytics (do not store message text, seed payloads, request bodies, spoiler content).
- No direct user identity analytics (no usernames, Discord IDs, OAuth identifiers, IP addresses in telemetry records).
- No behavior profiling across long-lived individuals.

## 2. Privacy and Data Policy

## Telemetry policy contract

- **Anonymous by design:** records must be aggregate-safe and identity-minimized.
- **Data minimization:** capture only fields required for feature usage and reliability metrics.
- **Retention limit:** short retention window (default 30 days) with scheduled purge.
- **Operator transparency:** include a user-facing telemetry statement in docs and admin-facing command/help output.

## Allowed fields

- `event_name` (e.g., `discord.seed.generate`)
- `surface` (`discord`, `racetime`, `api`)
- `feature` (`generator`, `daily`, `asynctournament`, etc.)
- `action` (`invoke`, `success`, `failure`)
- `status` (`ok`, `error`, `timeout`, `denied`)
- `provider` (optional; randomizer provider/API name)
- `guild_hash` (optional, salted one-way hash of guild ID)
- `day_bucket` (UTC date only)
- `duration_ms` (optional)
- `error_type` (normalized domain error only)

## Disallowed fields

- Raw Discord user IDs, usernames, discriminators
- OAuth user identifiers/session tokens
- Raw guild/channel IDs in telemetry storage
- Raw command arguments when they can contain identifying/custom text
- Request IP addresses or user-agent strings
- Full exception stack traces in telemetry records

## 3. Architecture Plan

Implement a shared telemetry service in core utilities and use it from all execution surfaces.

## Proposed modules

- `alttprbot/util/telemetry.py`
  - `TelemetryEvent` dataclass (validated, minimal schema)
  - `TelemetryService` interface (`record`, `record_timing`, `flush`)
  - `NoOpTelemetryService` for disabled mode
  - `DatabaseTelemetryService` for production storage
- `alttprbot/models/models.py`
  - new `TelemetryEvent` ORM model/table
- `alttprbot_discord/*`, `alttprbot_racetime/*`, `alttprbot_api/*`
  - thin instrumentation hooks at command/route/handler boundaries

## Event flow

1. Surface boundary receives command/request.
2. Emit `*.invoke` event.
3. Execute feature logic.
4. Emit terminal event: `*.success` or `*.failure` with normalized status/error.
5. Batch write to DB asynchronously (small queue, bounded size).

## Safety controls

- Feature flag: `TELEMETRY_ENABLED` (default `false` until rollout).
- Bounded in-memory queue to avoid unbounded growth.
- Fail-open behavior: telemetry failures never break user-facing flows.
- Optional periodic flush task per process.

## 4. Event Taxonomy (MVP)

Start with high-signal entrypoints rather than exhaustive instrumentation.

## Discord

- `discord.generator.invoke|success|failure`
- `discord.daily.announce.success|failure`
- `discord.asynctournament.run_start|run_submit|review_complete`
- `discord.racetime_tools.command.invoke|success|failure`

## RaceTime

- `racetime.room.command.invoke|success|failure`
- `racetime.seed.generate.success|failure`

## Web/API

- `api.auth.login.start|success|failure`
- `api.settingsgen.request.success|failure`
- `api.sglive.seed_generate.success|failure`

## Normalized error types

- `provider_unavailable`
- `provider_timeout`
- `invalid_preset`
- `permission_denied`
- `unexpected_error`

## 5. Data Model and Query Plan

## Table sketch

- `id` (pk)
- `created_at` (timestamp UTC)
- `day_bucket` (date)
- `event_name` (varchar, indexed)
- `surface` (varchar, indexed)
- `feature` (varchar, indexed)
- `action` (varchar)
- `status` (varchar, indexed)
- `provider` (nullable varchar)
- `guild_hash` (nullable varchar, indexed)
- `duration_ms` (nullable int)
- `error_type` (nullable varchar)
- `sample_rate` (float default 1.0)

## Recommended indexes

- `(day_bucket, surface, feature)`
- `(day_bucket, event_name)`
- `(day_bucket, status)`

## Baseline queries

- Daily feature usage counts by surface/feature/action.
- Success vs failure rates by feature and provider.
- P95 execution time by feature for latency-sensitive commands.
- Active guild count estimate (count distinct `guild_hash` per day, if enabled).

## 6. Rollout Phases

### Phase 0 — Design and Contracts

- Finalize telemetry schema and allowed/disallowed field policy.
- Add config contract in `config.py` / settings:
  - `TELEMETRY_ENABLED`
  - `TELEMETRY_SAMPLE_RATE` (default `1.0`)
  - `TELEMETRY_RETENTION_DAYS` (default `30`)
  - `TELEMETRY_HASH_SALT`
- Define exception-to-error-type mapping helper.

### Phase 1 — Storage and Service

- Add new ORM model and migration for telemetry table.
- Implement `DatabaseTelemetryService` with async buffered writes.
- Add scheduled retention purge job.
- Add no-op fallback service when disabled/misconfigured.

### Phase 2 — MVP Instrumentation

- Instrument top-priority Discord cogs:
  - `generator`, `daily`, `asynctournament`, `racetime_tools`
- Instrument RaceTime base command handling and seed generation handlers.
- Instrument high-value API routes (`/login`, `/callback/discord`, `settingsgen`, `sglive`).

### Phase 3 — Reporting and Operations

- Add reusable SQL/report helpers under `helpers/` for daily/weekly usage summaries.
- Publish operator runbook for reading usage metrics and validating telemetry health.
- Add Sentry breadcrumb/log-only alerts for telemetry queue overflow or flush failures.

### Phase 4 — Expansion

- Expand coverage to additional cogs/routes based on value.
- Consider pre-aggregated daily summary table if query volume grows.

## 7. Verification Strategy

- Unit tests for:
  - event validation and field filtering
  - hash function behavior and stability
  - exception normalization mapping
  - queue flush and fail-open behavior
- Integration tests (or local smoke scripts) for:
  - Discord command instrumentation path
  - RaceTime command instrumentation path
  - API route instrumentation path
- Manual validation:
  - run representative commands/routes with telemetry on
  - verify no prohibited fields are persisted
  - verify retention purge removes expired rows

## 8. Risks and Mitigations

- **Risk:** Event volume growth increases DB load.  
  **Mitigation:** sampling support, buffered writes, and scoped MVP events first.
- **Risk:** Developers accidentally log user-identifying payloads.  
  **Mitigation:** centralized event schema validator with explicit allowlist.
- **Risk:** Telemetry failure impacts runtime.  
  **Mitigation:** fail-open writes and bounded queue with drop counters.

## 9. Initial Implementation Checklist

- [ ] Add telemetry config keys and defaults.
- [ ] Add telemetry ORM model + Aerich migration.
- [ ] Implement shared telemetry service (`NoOp` + DB-backed).
- [ ] Add retention purge task.
- [ ] Instrument Discord MVP cogs.
- [ ] Instrument RaceTime MVP handlers.
- [ ] Instrument API MVP routes.
- [ ] Add `helpers/` usage report script(s).
- [ ] Document telemetry policy/runbook under `docs/guides/`.
- [ ] Enable in staging first, then production.
