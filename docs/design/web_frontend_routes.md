# Web Frontend Route Map

> Last updated: 2026-02-12
> Scope: HTML-rendered routes in `alttprbot_api/`

## Rendering Stack

- Framework: Quart (`alttprbot_api/api.py`)
- Templates: Jinja2 files under `alttprbot_api/templates/`
- Auth for human sessions: Discord OAuth via `quart_discord` (`@requires_authorization`)

## Intent Notes (confirmed 2026-02-12)

- DEBUG-only frontend blueprints (`/schedule/*`, `/user/*`) are unfinished features.
- Prefer treating these as feature-flagged surfaces instead of production routes.

## Top-Level App Pages

### GET /

- Attempts to fetch Discord user from OAuth session.
- Renders `index.html` with user context if logged in, else anonymous context.

### GET /login/

- Starts Discord OAuth session with `identify` scope.

### GET /callback/discord/

- Completes Discord OAuth callback and redirects to stored `redirect` target (default `/me/`).

### GET /me/ (auth required)

- Renders `me.html` for current Discord user.

### GET /logout/

- Revokes OAuth token and redirects to `/`.

### GET /purgeme

- Renders `purge_me.html` for current Discord user.

### POST /purgeme

- If `confirmpurge=yes`, deletes current user’s `PresetNamespaces` and `NickVerification` rows, then logs out.
- Otherwise redirects to `/me/`.

### Error Rendering

Error handlers render `error.html` for:

- Unauthorized (redirects to login after storing original path)
- Access denied
- 404 not found
- Invalid/expired Discord grants (`InvalidGrantError`, `TokenExpiredError`)
- 500 generic server error

## Blueprint: Presets (HTML)

Routes support namespace browsing and preset CRUD with template-driven pages.

- GET `/presets` → `preset_namespaces_all.html`
- GET `/presets/me` (auth) → creates/retrieves user namespace then redirects
- GET `/presets/<namespace>/create` (auth) → `preset_new.html` (owner-only)
- POST `/presets/<namespace>/create` (auth) → create preset from uploaded file
- GET `/presets/manage/<namespace>` → `preset_namespace.html`
- GET `/presets/manage/<namespace>/<randomizer>` → `preset_namespace.html` filtered by randomizer
- GET `/presets/manage/<namespace>/<randomizer>/<preset>` → `preset_view.html`
- GET `/presets/download/<namespace>/<randomizer>/<preset>` → file download
- POST `/presets/manage/<namespace>/<randomizer>/<preset>` (auth) → update/delete preset

## Blueprint: Async Tournament (HTML)

All routes are mounted under `/async`.

### Player-facing

- GET `/async/races/<tournament_id>` (auth): player dashboard (`asynctournament_dashboard.html`)
- GET `/async/races/<tournament_id>/reattempt` (auth): reattempt form (`asynctournament_reattempt.html`)
- POST `/async/race/<tournament_id>/reattempt` (auth): submit reattempt reason

### Reviewer/admin-facing

Authorization is checked by `checks.is_async_tournament_user(...)` for roles `admin` or `mod`.

- GET `/async/races/<tournament_id>/queue` (auth): filtered review queue (`asynctournament_race_list.html`)
- GET `/async/races/<tournament_id>/review/<race_id>` (auth): review screen (`asynctournament_race_view.html`)
- POST `/async/races/<tournament_id>/review/<race_id>` (auth): apply review status + notes

### Public/conditional visibility pages

- GET `/async/races/<tournament_id>/leaderboard`
- GET `/async/player/<tournament_id>/<user_id>`
- GET `/async/pools/<tournament_id>`
- GET `/async/permalink/<tournament_id>/<permalink_id>`

Visibility rules are conditional on tournament status, role checks, and permalink `live_race` behavior.

## Blueprint: Tournament Submission (HTML)

- GET `/submit/<event>` (auth): resolves event config and renders either event-specific template or generic `submission.html`.
- POST `/submit` (auth): processes submitted form via tournament handler and renders `submission_done.html` on success.

## Blueprint: Triforce Texts (HTML)

- GET `/triforcetexts/sgl23`: key-gated session-based submission page (`triforce_text.html`, no Discord auth required)
- POST `/triforcetexts/sgl23/submit`: validates 3-line text and submits with manual author field
- GET `/triforcetexts/<pool_name>` (auth): authenticated submission page
- POST `/triforcetexts/<pool_name>/submit` (auth): validates and submits using Discord identity
- GET `/triforcetexts/<pool_name>/moderation` (auth): moderator queue page
- GET `/triforcetexts/<pool_name>/moderation/<text_id>/<action>` (auth): approve/reject action

## Blueprint: Ranked Choice (HTML)

- GET `/ranked_choice/<election_id>` (auth): displays ballot or already-submitted view
- POST `/ranked_choice/<election_id>` (auth): validates and stores ranked votes, then renders confirmation

Private elections enforce membership in configured guild role.

## Blueprint: RaceTime Verification (HTML)

- GET `/racetime/verification/initiate` (auth): redirects user to RaceTime OAuth authorize endpoint
- GET `/racetime/verify/return` (auth): exchanges code for token, links/merges user records, renders `racetime_verified.html`

## Blueprint: SG Live Dashboard (HTML)

Mounted under `/sglive`.

- GET `/sglive/`: dashboard (`sglive_dashboard.html`) listing generator links
- GET `/sglive/generate/alttpr` → redirect to generated seed URL
- GET `/sglive/generate/ootr` → redirect to generated seed URL
- GET `/sglive/generate/smz3` → redirect to generated seed URL
- GET `/sglive/generate/smr` → redirect to generated seed URL
- GET `/sglive/generate/ffr` → redirect to generated seed URL
- GET `/sglive/generate/smz3/main` → redirect to generated seed URL
- GET `/sglive/reports/capacity` → capacity report page (`sglive_reports_capacity.html`)

Generation endpoints write history rows (`SGL2023OnsiteHistory`) with seed URL and request IP.

## DEBUG-only Frontend Surfaces

These blueprints are only registered when `config.DEBUG` is true.

### `/schedule/*`

Implemented pages:

- GET `/schedule/<slug>`
- GET `/schedule/<slug>/<episode_id>`
- GET `/schedule/<slug>/submit` (auth)
- POST `/schedule/<slug>/submit` (auth)

Stubbed/unimplemented handlers:

- GET `/schedule/<slug>/<episode_id>/signup`
- POST `/schedule/<slug>/<episode_id>/signup`

### `/user/*`

- GET `/user/<id>` currently returns plain text: `Not implemented yet`.

## Frontend Operation Summary

- Human identity and authorization are primarily session-based through Discord OAuth.
- Feature domains are segmented by blueprints and template groups.
- A single Quart process serves both HTML pages and non-HTML API surfaces.
