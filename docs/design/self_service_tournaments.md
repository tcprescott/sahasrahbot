# Self-Service Tournament System Design

> Last updated: 2026-06-12
> Scope: DB-backed, web-managed tournament definitions with pluggable seed rollers; custom code only where genuinely needed
> Status: Approved design — implementation not yet started

This design **supersedes** [Tournament Registry Config-Driven Design](tournament_registry_config_design.md) and its rollout plan (`plans/tournament_registry_config_rollout_plan.md`). The YAML registry path built in Phase 0/1 of that effort (slug→handler+enabled mapping behind `TOURNAMENT_CONFIG_ENABLED`, currently disabled) is a strict subset of the DB-backed record described here and will be **retired** once the DB path ships.

## Problem Statement

Every tournament — even pure boilerplate — requires a custom Python subclass of `TournamentRace`, a code deploy, and maintainer involvement. Analysis of the 23 existing subclasses:

| Category | Count | Examples | What actually varies |
|---|---|---|---|
| Pure config-only | 6 | `test`, `alttprcd`, `boots`, `nologic`, `alttprhmg`, `smwde` | `TournamentConfig` values + a preset name in `roll()` |
| Preset selection | 3 | `alttprde`, `alttprmini` (match-title→preset map), `smz3coop` | A title→preset mapping or fixed preset + coop flag |
| Declarative submission forms | 3 | `alttprfr`, `alttpres`, `smrl_playoff` | Form schema (`[{key, label, settings}]`) + settings→seed mapping |
| Genuinely custom | 8+ | `alttpr_quals`, `alttprleague`×2, `alttprsglive`, `smbingo`, `smrl`, dailies | External API integrations, BingoSync, multiworld, qualifier branching, open-entry announcements |

Roughly half the subclasses exist only to carry configuration values. The goal: **authorized users set up and manage tournaments self-service via the web UI**, with custom code reserved for genuinely custom behavior (seed rollers, lifecycle integrations).

## Decisions (owner-confirmed, 2026-06-12)

1. **Retire the YAML registry** (`config/tournaments.yaml`, `alttprbot/tournament/registry_loader.py`, `TOURNAMENT_CONFIG_ENABLED`) once the DB path is live. The DB rows are the enable/disable toggle the YAML was for.
2. **Organizer trust authorization model**: a `tournament_organizer` flag granted by the bot owner is the approval gate. Organizers create and activate their own tournaments freely; no per-tournament approval queue.

## Architecture Overview

```
Tournament (DB record, web-editable)
  ├── handler: 'generic' → DynamicTournamentRace        (covers ~12 boilerplate tournaments)
  │             or named custom class                   (quals, league, bingo, smrl, sgl, dailies)
  ├── seed_roller: named entry in ROLLER_REGISTRY + roller_config JSON
  ├── submission_form: declarative JSON schema (optional)
  └── all TournamentConfig values as raw Discord/RaceTime IDs

get_active_tournaments()  ← async, re-queried each loop cycle (no-restart reload)
  ├── DB rows where active=True and within season window
  └── merged with remaining code-defined handlers during transition
```

## 1. Data Model

New Tortoise models in `alttprbot/models/models.py`, one Aerich migration.

### `Tournament`

| Field | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `event_slug` | char(45), unique | SpeedGaming slug; registry key |
| `name` | char(200) | Display name |
| `active` | bool, default False | Replaces seasonal code/YAML toggling |
| `starts_at` / `ends_at` | datetime, null | Optional season window; loops skip outside it |
| `schedule_type` | char(20), default `'sg'` | Mirrors `TournamentConfig.schedule_type` |
| `handler` | char(45), default `'generic'` | Key into `AVAILABLE_TOURNAMENT_HANDLERS` |
| `seed_roller` | char(45), null | Key into `ROLLER_REGISTRY` |
| `roller_config` | JSON, null | Roller parameters, e.g. `{"preset": "casualboots"}` or `{"title_map": {...}}` |
| `guild_id` | bigint | |
| `racetime_category` | char(45) | Must exist in active racetime bots |
| `racetime_goal` | char(200) | |
| `audit_channel_id` / `commentary_channel_id` / `mod_channel_id` / `scheduling_needs_channel_id` | bigint, null | |
| `admin_role_ids` / `helper_role_ids` / `commentator_role_ids` / `mod_role_ids` | JSON, null | Lists of role IDs |
| `stream_delay` | smallint, default 0 | |
| `room_open_time` | smallint, default 35 | |
| `auto_record` / `coop` / `create_scheduled_events` / `scheduling_needs_tracker` | bool, default False | |
| `lang` | char(10), default `'en'` | |
| `submission_form` | JSON, null | Same `[{key, label, settings: {...}}]` shape `alttprfr.submission_form` uses today |
| `owner_id` | bigint | Creator's Discord ID |
| `created` / `updated` | datetime auto | |

### `TournamentPermission`

Mirror of `AsyncTournamentPermissions`: `tournament` FK, `user` FK (null) **or** `discord_role_id` (null), `role` ∈ {`admin`, `mod`}.

### `Users.tournament_organizer`

Boolean, default False. Granted via an owner-only Discord command (e.g. `/tournament grant_organizer @user`). Chosen over a separate grants table — single flag, no join, fits the single-maintainer scale.

### Unchanged

`TournamentGames`, `TournamentResults`, `TournamentPresetHistory`, `ScheduledEvents` — all keyed on `episode_id`/`event` strings and work as-is.

## 2. Seed Roller Plugin Registry

New file `alttprbot/tournament/rollers.py`.

**Interface:** `async def roll(race: TournamentRace, config: dict) -> seed`, registered by name. Each roller also exposes `validate(config) -> list[str]` (error messages) for API-side validation.

Initial rollers, wrapping existing generators in `alttprbot/alttprgen/generator.py` and routed through the provider reliability wrapper (`alttprbot/alttprgen/provider_wrapper.py`) where adapters exist:

| Roller | Config | Replaces |
|---|---|---|
| `alttpr_preset` | `{preset, allow_quickswap?, hints?, spoilers?, branch?}` | boots, nologic, alttprcd, alttprhmg |
| `alttpr_preset_map` | `{title_map: {...}, default?}` — strips `"x:"` prefix from `match1.title` | alttprde, alttprmini |
| `alttpr_settings` | `{settings_template}` — base settings dict with `{key}` substitution from submitted `TournamentGames.settings` | alttprfr, alttpres |
| `alttpr_mystery` | `{weightset}` | mystery-style events |
| `smz3_preset` | `{preset}` | smz3coop |
| `sm_preset` | `{randomizer, preset}` (SMPreset/SMVaria/SMDash) | future SM events |

Future one-off tournaments add a named roller function here — **no subclass, no new lifecycle code**. The roller's returned seed object carries game-type specifics (embed methods, `seed_code` format); the generic handler tolerates seeds lacking `tournament_embed`/`code` by falling back to a plain embed / no code.

## 3. Generic Handler: `DynamicTournamentRace`

New file `alttprbot/tournament/dynamic.py`. Subclasses `ALTTPRTournamentRace` (`alttprbot/tournament/alttpr.py`), which already implements the full `process_tournament_race` → roll → embeds → audit/commentary/DM flow.

- **Construction:** built around a `Tournament` DB record. Because consumers (`alttprbot_discord/cogs/tournament.py`, `alttprbot/tournaments.py`) call classmethods (`get_config`, `construct`, `construct_with_episode_data`, `construct_race_room`), a small factory `make_dynamic_handler(record)` returns a lightweight wrapper exposing the same classmethod-shaped API with the record closed over. Call sites stay shape-compatible.
- **`configuration()`:** builds `TournamentConfig` by resolving the record's raw IDs through the live `discordbot` (`get_guild`/`get_channel`/`guild.get_role`) — exactly what every subclass does by hand today. Resolved at construction time; records are re-read each poll cycle so edits apply to the next room.
- **`roll()`:** `await ROLLER_REGISTRY[record.seed_roller](self, record.roller_config or {})`.
- **`submission_form` / `process_submission_form`:** form schema comes from `record.submission_form` (the existing `/api/tournament/form-config/<event>` endpoint already serves list-shaped forms). Generic processing: validate payload keys against the schema, store in `TournamentGames.settings`, send confirmation embeds to audit channel + players — lifted from `alttprfr.process_submission_form` minus the FR-specific settings mapping. The FR/ES transform of answers→randomizer settings moves into the `alttpr_settings` roller's `settings_template`; anything fancier earns a custom roller.

## 4. Registry Redesign (`alttprbot/tournaments.py`)

Replace the module-load-time `TOURNAMENT_DATA` dict with an async accessor:

```python
async def get_active_tournaments() -> dict[str, handler]:
    records = await models.Tournament.filter(active=True)   # + season-window filter
    registry = {r.event_slug: make_handler(r) for r in records}
    for slug, cls in _CODE_DEFINED.items():                 # transition merge
        registry.setdefault(slug, cls)
    return registry
```

- `make_handler(record)`: `handler == 'generic'` → `make_dynamic_handler(record)`; otherwise the custom class from `AVAILABLE_TOURNAMENT_HANDLERS` (custom classes may optionally consume a `db_record` kwarg for config values — Phase D).
- `AVAILABLE_TOURNAMENT_HANDLERS` becomes the handler registry: the ~8 custom classes plus `'generic'`.
- **Consumers** re-query at the top of each cycle: the `create_races` (5 min), `week_races` (15 min), and `find_races_with_bad_discord` (240 min) loops in `alttprbot_discord/cogs/tournament.py`; `fetch_tournament_handler` / `fetch_tournament_handler_v2` / `create_tournament_race_room`; and `TOURNAMENT_DATA` lookups in `alttprbot_api/blueprints/tournament.py`.
- **Runtime reload falls out for free**: per-cycle DB reads (a handful of rows) mean UI edits take effect without restart and without any cache-invalidation machinery. Rooms already in flight keep their constructed config, which is the desired behavior.
- **YAML retirement**: delete `registry_loader.py`, `config/tournaments.yaml`, `helpers/validate_tournament_config.py`, and the `TOURNAMENT_CONFIG_ENABLED` dual-path switch once the DB path is live. Keep `_HARDCODED_TOURNAMENT_DATA` only as the transition merge fallback, removed in Phase D.

## 5. Authorization

| Action | Who |
|---|---|
| Grant organizer | Bot owner (owner-only Discord command) |
| Create tournament | `Users.tournament_organizer == True` |
| Edit / activate / deactivate / manage permissions | Record owner, `TournamentPermission` admin (direct user or held Discord role), or bot owner |
| Per-tournament moderation surfaces (future) | `TournamentPermission` mod |

Role resolution reuses the `is_async_tournament_user` pattern from `alttprbot_api/util/checks.py` (checks explicit user grants, then Discord role membership via the live guild). Web auth is the existing Authlib Discord OAuth session flow.

The organizer grant **is** the approval step — no per-tournament approval queue (owner-confirmed; a queue is overengineering at this user count).

## 6. API + SPA

### Quart endpoints (extend `alttprbot_api/blueprints/tournament.py`)

| Route | Purpose |
|---|---|
| `GET /api/tournament/manage` | List tournaments the current user can manage |
| `POST /api/tournament/manage` | Create (organizer only) |
| `GET/PUT /api/tournament/manage/<id>` | Read / update full record |
| `POST /api/tournament/manage/<id>/activate` & `/deactivate` | Toggle active |
| `GET/POST/DELETE /api/tournament/manage/<id>/permissions` | Permissions CRUD |
| `GET /api/tournament/meta` | Roller keys + per-roller param hints, handler keys, bot guilds → channels/roles for pickers (the API shares the live `discordbot` object) |

Server-side validation: slug uniqueness, racetime category exists among active racetime bots, guild/channel/role IDs resolvable, roller key exists, `roller_config` passes the roller's `validate()`, submission-form shape check.

### SPA pages (`alttprbot_api/spa/src/pages/tournament-admin/`)

Follow the async-tournament page patterns (`pages/async-tournament/*`, `hooks/useMe.ts`, shared UI components):

- `TournamentListPage.tsx` — list with active toggle.
- `TournamentEditPage.tsx` — single form: basics, guild→channel/role pickers fed by `/api/tournament/meta`, racetime fields, timing, roller dropdown + dynamic config sub-form, submission-form builder, permissions table.
- Routes registered in `router.tsx`.

**v1 pragmatism:** validated JSON textareas for `roller_config` and `submission_form` are acceptable; pretty builders (title-map key/value editor, form-field rows) are v2.

## 7. Phased Rollout

| Phase | Content | Risk |
|---|---|---|
| **A** | Models + Aerich migration + async `get_active_tournaments()` with code-defined merge; convert consumers to async lookup. DB empty; no behavior change. | Low — pure refactor, hardcoded registry still authoritative |
| **B** | `rollers.py` + `DynamicTournamentRace` + factory. Convert in risk order: `test` (DEBUG validation) → 6 config-only → `alttprde`/`alttprmini` (preset-map) → `smz3coop` → `alttprfr`/`alttpres`/`smrl_playoff` (forms + settings-template). Insert DB row, retire subclass (keep file dead one season for rollback). | Near zero — all are currently-disabled seasonal events; validate via `test` slug in DEBUG |
| **C** | Web CRUD endpoints + SPA admin pages + organizer grant command. Until then, manual DB rows are the interim. | Low |
| **D** | Register the 8 custom handlers as selectable `handler` values; move their `configuration()` constants into DB rows incrementally. Delete YAML registry, `registry_loader.py`, and the hardcoded dict. | Low, lowest priority — they work today |

## Trade-offs Considered

1. **Approval queue vs organizer trust** — chose trust; the organizer grant is the gate (owner-confirmed).
2. **Registry cache vs per-cycle DB read** — chose per-cycle read; eliminates invalidation entirely at negligible query cost.
3. **Generic form→settings mapping** — chose declarative `settings_template` over arbitrary code hooks; covers FR/ES, anything beyond becomes a named custom roller.
4. **YAML** — retire, don't absorb; it never went live and duplicates a subset of the DB record (owner-confirmed).

## Related Documents

- [Tournament System Analysis](tournament_system_analysis.md) — current-state architecture this design builds on
- [Tournament Module (Non-Async) Audit](tournament_module_non_async_audit.md) — reliability findings
- [Tournament Registry Config-Driven Design](tournament_registry_config_design.md) — **superseded** by this document
- [Seed Provider Reliability Contract](seed_provider_reliability_contract.md) — rollers route through this wrapper
- [Async Tournament Discord Workflow](async_tournament_discord_workflow.md) — source of the permissions pattern reused here
