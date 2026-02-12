# Web API JSON Endpoints

> Last updated: 2026-02-12
> Scope: JSON-producing endpoints under `alttprbot_api/`

## Runtime Registration

The Quart app is created in `alttprbot_api/api.py` and registers JSON routes from multiple blueprints:

- `settingsgen` (no URL prefix)
- `tournament` (no URL prefix)
- `presets` (no URL prefix)
- `racetime` (no URL prefix)
- `asynctournament` (registered with `/async` prefix)

## Authentication Modes

Two auth modes are used by JSON endpoints:

- **Application auth key** via `Authorization` header (`auth.authorized_key(...)`), backed by `AuthorizationKeyPermissions` records.
- **Querystring auth key** for one legacy endpoint (`/api/racetime/cmd?auth_key=...`), validated against `AuthorizationKeyPermissions` with `type='racetimecmd'` and category subtype.

Author intent confirmed 2026-02-12:

- `@requires_authorization` routes are intended for humans.
- `authorized_key` routes are intended for applications.
- Future direction: unify auth/authz so REST API keys are user-generated.

## Endpoint Inventory

## Settings Generation

### POST /api/settingsgen/mystery

- Request body: JSON weights object.
- Flow: builds `ALTTPRMystery.custom_from_dict(weights)`, then runs `generate_test_game()`.
- Response: JSON object with:
  - `settings`
  - `customizer` (bool)
  - `doors` (bool)
  - `endpoint` (`/api/customizer`, `/api/randomizer`, or `null` for doors)

### GET /api/settingsgen/mystery

- Query params: optional `weightset`.
- Flow: builds `ALTTPRMystery(preset=weightset)` and runs `generate_test_game()`.
- Response shape matches POST.

### GET /api/settingsgen/mystery/<weightset>

- Path param: `weightset`.
- Flow and response shape match the GET endpoint above.

## Tournament Data

### GET /api/tournament/games

- Query params: all query args are passed directly to `TournamentGames.filter(**terms)`.
- Response: `jsonify(data)` where `data` is `values()` output from Tortoise ORM.

## Presets API

### GET /presets/api/<randomizer>/list

- Supported randomizers by hardcoded map: `alttpr`, `smz3`, `sm`, `alttprmystery`, `ctjets`.
- Flow:
  - Loads global presets from generator class.
  - Loads namespace presets from DB (`PresetNamespaces` + filtered `Presets`).
- Response:
  - `global`: list of global preset names.
  - `namespaces`: list of `{name, presets[]}` for namespaces with at least one matching preset.

### GET /presets/api/<randomizer>?preset=<name>

- Query param: `preset`.
- Flow: instantiates mapped generator with requested preset and calls `fetch()`.
- Success response: `{ preset, randomizer, data }`.
- Not found behavior: returns `{}`.

## RaceTime Command API

### POST /api/racetime/cmd?auth_key=<key>

- Request body JSON: `category`, `room`, `cmd`.
- Authz: checks `AuthorizationKeyPermissions` by key + `type='racetimecmd'` + category subtype.
- Flow:
  - Resolves in-memory RaceTime bot and room handler.
  - Constructs synthetic chat payload.
  - Sends status message and executes command via handler chat pipeline.
- Response: `{ "success": true }`.

Author intent confirmed 2026-02-12:

- Purpose is programmatic command relay from external bots/services (for example, another RaceTime bot asking SahasrahBot to roll a seed on a user’s behalf).

## Async Tournament API (all routes prefixed with /async)

All endpoints in this section require `Authorization` header and `authorized_key('asynctournament')`.

### GET /async/api/tournaments

- Optional filter: `active=true|false`.
- Response: pydantic JSON list of `AsyncTournament`.

### GET /async/api/tournaments/<tournament_id>

- Response: pydantic JSON object for one `AsyncTournament`.
- Not found: `{ "error": "Tournament not found." }`.

### GET /async/api/tournaments/<tournament_id>/races

- Optional filters: `id`, `user_id`, `permalink_id`, `pool_id`, `status`.
- Pagination: `page` (default 1), `page_size` (default 20, max 100).
- Response: pydantic JSON list of `AsyncTournamentRace`.
- Validation: aborts 400 if `page_size > 100`.

### GET /async/api/tournaments/<tournament_id>/pools

- Optional filter: `id`.
- Response: pydantic JSON list of `AsyncTournamentPermalinkPool`.

### GET /async/api/tournaments/<tournament_id>/permalinks

- Optional filters: `id`, `pool_id`.
- Response: pydantic JSON list of `AsyncTournamentPermalink`.

### GET /async/api/tournaments/<tournament_id>/leaderboard

- Flow: loads tournament, computes leaderboard via `alttprbot.util.asynctournament.get_leaderboard(...)`.
- Response: custom JSON array containing:
  - `player` object
  - `score`
  - `rank`
  - `races[]` with race scoring/timing fields
  - `counts` (`finished`, `forfeited`, `unplayed`)
- Not found: `{ "error": "Tournament not found." }`.

## Operational Notes

- The app serves static content via `/assets/<path>` and `/theme-assets/<path>`, but these are file-serving routes, not JSON API endpoints.
- `/healthcheck` is JSON (`{ success: true }`) and verifies Discord bot availability by calling `application_info()` and fetching owner user.
- `OAUTHLIB_INSECURE_TRANSPORT` is set to `1` in app startup, allowing non-HTTPS OAuth transport in runtime configuration.
