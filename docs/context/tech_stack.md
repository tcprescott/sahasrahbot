# Tech Stack

> Last updated: 2026-02-12

## Runtime

| Component | Version | Notes |
|-----------|---------|-------|
| Python | ^3.11 | Required minimum |
| Poetry | — | Dependency management and virtual environment |

## Core Frameworks

| Library | Version | Purpose |
|---------|---------|---------|
| `discord.py` | `*` (latest) | Discord bot framework (v2.x with slash commands) |
| `quart` | `*` (latest) | Async web framework (Flask-compatible) |
| `Quart-Discord` | `>=2.1.4` | Discord OAuth2 integration for Quart |
| `racetime-bot` | pinned commit `48afdd4` | RaceTime.gg bot SDK (custom fork by tcprescott) |
| `tortoise-orm` | via `aerich` | Async ORM for MySQL |
| `aerich` | `>=0.5.5` | Database migration tool for Tortoise ORM |

## Database

| Component | Details |
|-----------|---------|
| Engine | MySQL |
| Driver | `aiomysql` (`>=0.0.20`) |
| ORM | Tortoise ORM |
| Migrations | Aerich (97 migrations, SQL + Python format) |

## Randomizer Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| `pyz3r` | `^6.0.7` | ALTTPR Python library (seed gen, mystery, spoiler parsing) |

## HTTP / Networking

| Library | Version | Purpose |
|---------|---------|---------|
| `aiohttp` | `*` | Async HTTP client for API calls |
| `aioboto3` | `>=8.0.5` | Async AWS SDK (S3 operations) |

## Caching

| Library | Version | Purpose |
|---------|---------|---------|
| `aiocache` | `>=0.11.1` | Async in-memory caching (SimpleMemoryCache) |

## Google Integration

| Library | Version | Purpose |
|---------|---------|---------|
| `gspread-asyncio` | `*` | Async Google Sheets client |
| `oauth2client` | `*` | Google OAuth2 service account auth |
| `google-api-python-client` | `*` | Google APIs client library |

## Data Processing

| Library | Version | Purpose |
|---------|---------|---------|
| `PyYAML` | `*` | YAML preset file parsing |
| `dataclasses-json` | `*` | JSON serialization for dataclasses |
| `isodate` | `*` | ISO 8601 duration parsing |
| `html2markdown` | `*` | HTML-to-markdown conversion |
| `html5lib` | `*` | HTML parsing |
| `markdown` | `^3.4.3` | Markdown rendering |
| `emoji` | `*` | Emoji handling |

## Utilities

| Library | Version | Purpose |
|---------|---------|---------|
| `python-slugify` | `*` | URL-safe slug generation |
| `shortuuid` | `*` | Short unique ID generation |
| `urlextract` | `*` | URL extraction from text (used in moderation) |
| `pyrankvote` | `*` | Single Transferable Vote counting |
| `aiofiles` | `>=0.4.0` | Async file I/O |

## Runtime Import vs Declared Dependency Drift

The following libraries are imported in runtime code but are not currently declared in `pyproject.toml` dependencies:

- `tenacity`
- `python-dateutil` (`dateutil`)
- `pytz`

Treat these as environment-coupled dependencies until Poetry declarations are reconciled.

## Monitoring

| Library | Version | Purpose |
|---------|---------|---------|
| `discord-sentry-reporting` | `*` | Sentry integration for discord.py |
| `sentry_sdk` | (transitive) | Error tracking and reporting |

## Twitch Integration

| Library | Version | Purpose |
|---------|---------|---------|
| `twitchapi` | `^3.10.0` | Twitch API client |

## Discord Extensions

| Library | Version | Purpose |
|---------|---------|---------|
| `jishaku` | `*` | Debug/REPL extension for discord.py |

## Dev Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| `pycodestyle` | `*` | Python style checker |
| `pylint` | `*` | Python linter |
| `autopep8` | `^2.0.1` | Auto-formatter |
| `ipython` | `^8.10.0` | Interactive Python shell |

## Infrastructure

| Service | Purpose |
|---------|---------|
| AWS S3 | Spoiler log storage, patch distribution |
| MySQL | Primary database |
| Sentry | Error tracking (optional, configured via `SENTRY_URL`) |

## Configuration / Runtime Contracts

- Configuration behavior is defined in `config.py` and consumed as module-level constants across subsystems.
- API OAuth transport currently sets `OAUTHLIB_INSECURE_TRANSPORT=1` at startup.
- API session secret uses `APP_SECRET_KEY` (currently defaulting to empty string if unset).
- RaceTime per-category OAuth credentials are dynamically resolved using category-derived names:
	- `RACETIME_CLIENT_ID_<CATEGORY_SLUG_UPPER_NO_DASH>`
	- `RACETIME_CLIENT_SECRET_<CATEGORY_SLUG_UPPER_NO_DASH>`

## External APIs Consumed

| API | Authentication | Purpose |
|-----|---------------|---------|
| alttpr.com | Optional username/password | ALTTPR seed generation |
| sm.samus.link / samus.link | None | SM/SMZ3 seed generation |
| randommetroidsolver.pythonanywhere.com | None | SM Varia Randomizer |
| dashrando.net | None | SM Dash Randomizer |
| ctjot.com | None (web scraping) | CT Jets of Time |
| ootrandomizer.com | API key | OoT Randomizer |
| avianart.games | None | ALTTPR fork |
| bingosync.com | None (web scraping) | Bingo rooms |
| speedgaming.org | None | Tournament scheduling |
| racetime.gg | OAuth2 client credentials | Race room management |
| alttprleague.com | None | League mode/preset data |
| alttprladder.com | None | Racer verification |
| Google Sheets API | Service account | Results recording |
| Discord API | Bot token + OAuth2 | Bot interactions + web auth |
