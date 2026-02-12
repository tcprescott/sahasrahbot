# Seed Generation Component Audit

> Last updated: 2026-02-12  
> Scope: Discord generation cogs, RaceTime seed handlers, and web/API generation routes  
> Out of scope: non-async tournament module `alttprbot/tournament/*` roll paths

## Purpose

This document audits how seeds are generated across production-facing surfaces, with emphasis on component boundaries, flow consistency, and implementation risks.

## Component Boundary

Included modules:

- `alttprbot/alttprgen/generator.py`
- `alttprbot/alttprgen/preset.py`
- `alttprbot/alttprgen/spoilers.py`
- `alttprbot/alttprgen/smvaria.py`
- `alttprbot/alttprgen/smz3multi.py`
- `alttprbot/alttprgen/randomizer/*` generation backends used by scoped entrypoints
- `alttprbot_discord/cogs/generator.py`
- `alttprbot_discord/cogs/smmulti.py`
- `alttprbot_discord/cogs/asynctournament.py` (seed-pool generation paths)
- `alttprbot_discord/util/alttpr_discord.py`
- `alttprbot_discord/util/alttprdoors_discord.py`
- `alttprbot_discord/util/sm_discord.py`
- `alttprbot_discord/util/avianart_discord.py`
- `alttprbot_racetime/handlers/alttpr.py`
- `alttprbot_racetime/handlers/smr.py`
- `alttprbot_racetime/handlers/smz3.py`
- `alttprbot_api/blueprints/settingsgen.py`
- `alttprbot_api/blueprints/sglive.py` (seed generation endpoints)

Excluded by scope decision:

- `alttprbot/tournament/*` non-async tournament `roll()` implementations.

## Verified Intent (Owner-Confirmed)

The following intent statements are confirmed and not inferred:

- Scope priority for this audit is Discord generation cogs, RaceTime handlers, and web/API generation routes.
- Race and tournament generation defaults to spoiler-off primarily for fair-play anti-spoiler control.
- Reliability behavior should be standardized across external seed providers (retries/timeouts everywhere).
- When trade-offs conflict in this audit, prioritize developer ergonomics.

## Architecture Overview

### Core model

- `SahasrahBotPresetCore` provides preset fetch/search/save and namespace handling.
- `PRESET_CLASS_MAPPING` dispatches randomizer keys to concrete generator classes.
- Concrete classes (`ALTTPRPreset`, `ALTTPRMystery`, `SMPreset`, `SMZ3Preset`, `CTJetsPreset`) implement provider-specific generation and audit logging.
- Generation writes `AuditGeneratedGames` for most provider classes in `generator.py`.

### Provider adapters

- ALTTPR API and embeds: `ALTTPRDiscord`.
- Door randomizer local subprocess pipeline: `AlttprDoor` / `AlttprDoorDiscord`.
- AVIANART API polling flow: `AVIANART` / `AVIANARTDiscord`.
- Samus Link (SM/SMZ3): `SMDiscord`, `SMZ3Discord`.
- Spoiler upload path: `spoilers.write_json_to_disk()` to S3 (gzip payload).

### Runtime entry surfaces

- Discord slash commands (`/alttpr preset`, `/alttpr mystery`, `/sm`, `/smz3`, `/smdash`, `/ctjets`, custom preset/weightset upload paths).
- Discord async tournament admin tooling that pre-generates permalink pools.
- RaceTime text-command handlers (`!newrace`, `!mystery`, `!multiworld`, `!dash`, etc.).
- Web/API routes for mystery settings generation and SGLive event seed generation.

## End-to-End Flow by Surface

### Discord command generation

1. Command validates/selects preset or uploaded YAML.
2. Generator class resolves preset from global YAML or namespaced DB row.
3. Provider-specific generate path executes (ALTTPR, samus.link, DASH, CTJets, etc.).
4. Result is rendered into embed/message and returned to Discord.
5. Audit records are written for class-backed generators in `generator.py`.

### RaceTime generation

1. Handler command parses arguments and enforces room lock/team constraints.
2. Handler calls core generator class or provider helper.
3. Handler updates room race info and posts generated URL(s).
4. For spoiler races, spoiler URLs are scheduled through delayed delivery flow.

### Web/API generation

1. Blueprint endpoint receives request arguments.
2. Endpoint calls generator class or provider helper directly.
3. Endpoint returns JSON settings payload (`settingsgen`) or redirects to generated seed URL (`sglive`).

## Observed Design Strengths

- Clear separation between preset orchestration and provider-specific adapters.
- Shared preset abstraction (`SahasrahBotPresetCore`) supports global and namespaced presets consistently.
- Strong reuse of generation primitives across Discord, RaceTime, and API surfaces.
- Spoiler race support is first-class via dedicated spoiler generation and delayed reveal scheduling.

## Findings and Risks

## 1) Reliability behavior is inconsistent across providers

- `ALTTPRMystery.generate` includes retries for specific HTTP errors.
- Several other providers/paths use single-attempt calls or broad exception handling.
- External dependencies (DASH, CTJets, AVIANART polling, samus.link) do not share a common timeout/retry contract.

Impact:

- User-facing behavior differs by game/provider under transient failure.
- Operational diagnosis is harder due to uneven error semantics.

## 2) Audit logging coverage is uneven by entrypoint

- Generator classes in `generator.py` persist `AuditGeneratedGames`.
- Some direct helper/provider calls outside those classes (e.g., DASH helper paths) do not inherently log the same structured audit record.

Impact:

- Verification and post-incident tracing are stronger for some randomizers than others.

## 3) Sync file I/O inside async generation path

- `ctjets.roll_ctjets` performs synchronous ROM file read (`open('/opt/data/chronotrigger.sfc', 'rb')`) inside an async workflow.

Impact:

- Potential event-loop blocking under load.

## 4) Cross-layer coupling increases maintenance cost

- Core generator module imports Discord utility classes directly for return types and provider calls.

Impact:

- Non-Discord surfaces still depend on Discord-layer adapters, increasing coupling and test complexity.

## 5) Error typing and propagation differ widely

- Some paths raise typed domain exceptions (`PresetNotFoundException`).
- Others raise generic `Exception` with provider-specific strings.

Impact:

- Inconsistent handling at command/router layers and inconsistent user messaging.

## 6) Duplicate generation patterns across surfaces

- Similar generation argument handling and response composition appear in Discord cogs and RaceTime handlers.

Impact:

- Behavior drift risk when one surface is updated without the others.

## Policy/Contract Notes

- Spoiler-off default for race/tournament is an explicit fair-play control and should be treated as a policy contract.
- Standardized retry/timeout behavior across providers is now an explicit desired contract.
- Non-async tournament roll paths are intentionally excluded from this audit boundary.

## Suggested Stabilization Backlog

1. Define shared provider reliability contract (timeout, retry count, retryable status/errors, telemetry fields).
2. Implement a common provider execution wrapper and migrate all generation backends to it.
3. Normalize exception taxonomy for generation failures (`ProviderUnavailable`, `InvalidPreset`, `GenerationTimeout`, etc.).
4. Unify audit logging by adding a single logging hook for all seed generation entrypaths (including helper-only providers).
5. Move provider adapters to a generation-layer interface so core generation does not import Discord utility modules directly.
6. Refactor duplicate argument/response assembly into reusable service helpers consumed by Discord/RaceTime/API routes.

## Open Questions

- Should standardized retries/timeouts be globally identical, or allow small provider-specific overrides under a shared baseline policy?
- Should all non-class helper-based providers (for example DASH) be wrapped by class-based generators to guarantee audit/logging parity?