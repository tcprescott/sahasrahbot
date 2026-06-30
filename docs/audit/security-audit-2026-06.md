# Security Audit — June 2026

> Scope: SahasrahBot (`alttprbot/`) — the async monolith serving the Discord bot,
> audit bot, RaceTime.gg bot, and Quart web API over a shared MySQL/Tortoise DB.
> The web API and the seed-generation path are the realistic external attack
> surface, so the review concentrated there.

## Methodology

1. **Fan-out review** — three parallel read-only sweeps covering
   (a) authentication / secrets / OAuth / session handling,
   (b) injection / deserialization / SSRF / input handling, and
   (c) web-API hardening / dependencies / transport.
2. **Manual verification** — every candidate finding was confirmed by reading the
   actual service, repository, and authorization code. Several agent-suggested
   "IDOR" issues did **not** survive verification and are recorded below as
   refuted so future readers don't re-chase them.

**Overall posture is good.** No SQL injection (Tortoise ORM throughout, no raw
SQL / `.raw()` / string-formatted queries), no command injection
(`asyncio.create_subprocess_exec` with argument lists, never `shell=True`), no
unsafe deserialization (`yaml.safe_load` everywhere), no SSRF (outbound URLs are
hardcoded or config-sourced), and the Discord OAuth flow already generates and
validates a CSRF `state`. The findings are real but predominantly Medium/Low
hardening items.

## Findings

| # | Severity | Finding | Location | Status |
|---|----------|---------|----------|--------|
| 1 | High | Session cookie lacked `Secure`/`SameSite`; no `SameSite` defense for cookie-authed POSTs | `presentation/api/api.py` | Fixed |
| 3 | Medium | Protocol-relative open redirect after login (`//evil.com`) | `presentation/api/api.py`, `oauth_client.py` | Fixed |
| 4 | Medium | API key read from the URL **query string** (lands in access logs/proxies) | `presentation/api/blueprints/racetime.py` | Fixed (header added; query deprecated) |
| 5 | Medium | RaceTime account-link callback had no OAuth `state` (account-linking CSRF) | `presentation/api/blueprints/racetime.py` | Fixed |
| 6 | Medium | Verbose exception text reflected to API clients | `presentation/api/blueprints/tournament.py` | Fixed |
| 7 | Medium | Unguarded `base64.b64decode` on user-supplied preset data → crash/DoS | `services/seedgen/generator.py` | Fixed |
| 8 | Low/Med | Core deps pinned to `*` (`quart`/`authlib`/`aiohttp`/`tortoise-orm`/…) | `pyproject.toml` | Fixed |
| 9 | Low | `page` query param had no bounds (`page_size` did) | `presentation/api/blueprints/asynctournament.py` | Fixed |
| 10 | Low | 42 MB of dead vendored JS (`jquery-1.12.3` with XSS CVEs) | `presentation/api/static/theme-assets/` | Fixed (deleted) |

### 1 — Session cookie hardening (High)

`Quart` enables `HttpOnly` by default, but `Secure` and `SameSite` were unset, so
the session cookie carrying the Discord OAuth token could ride over plain HTTP and
offered no cookie-level CSRF defense for the state-changing `POST` endpoints
(`/purgeme`, preset create/update, async-tournament reattempt/review submit).

**Fix:** set `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'`, and
`SESSION_COOKIE_SECURE=not config.DEBUG`. `Lax` preserves the top-level GET OAuth
redirect while blocking cross-site POST forgery; `Secure` is relaxed under DEBUG
so local HTTP development still works.

### 3 — Open redirect after login (Medium)

After OAuth, the user is redirected to `login_original_path` (captured from
`request.full_path`). A request to a protocol-relative path such as
`//evil.com/x` would be stored verbatim and then issued as a `Location`, which
browsers treat as off-site.

**Fix:** added `_safe_redirect_target()`, which accepts a target only if it begins
with a single `/` (rejecting absolute and `//` protocol-relative URLs), applied at
both the `login()` read point and the `callback()` redirect, falling back to `/me`.

### 4 — API key in query string (Medium)

`/api/racetime/cmd` read its capability key from `?auth_key=`, which leaks into
web-server access logs, proxies, and browser history.

**Fix:** `_extract_auth_key()` now reads `Authorization: <key>` (or `Bearer <key>`)
first and falls back to the legacy `?auth_key=` query parameter, logging a
deprecation warning when the query form is used. **Deprecation:** the
`?auth_key=` form remains supported for now; existing callers should migrate to the
`Authorization` header. A missing key now returns `401` instead of `KeyError`/500.

### 5 — RaceTime account-link CSRF (Medium)

The RaceTime verification flow (`/racetime/verification/initiate` →
`/racetime/verify/return`) carried no OAuth `state`, so an attacker could trick a
logged-in victim into linking the **attacker's** RaceTime account to the victim's
Discord identity via a forged callback.

**Fix:** generate `secrets.token_urlsafe(32)` at initiate, store it in the session,
include it on the authorize URL, and validate it with `secrets.compare_digest`
(then pop it) before exchanging the code — mirroring the Discord OAuth pattern.

### 6 — Verbose error disclosure (Medium)

`/api/tournament/submit` returned `f"Invalid input: {e}"` / `f"Error processing
submission: {e}"`, reflecting raw exception text to clients.

**Fix:** log the exception server-side (`logger.warning(..., exc_info=True)` /
`logger.exception(...)`) and return generic messages.

### 7 — base64 decode DoS (Medium)

In the customizer path, `base64.b64decode(location).decode("utf8")` ran inside a
log statement on a `location` value taken from user-supplied preset
`forced_locations`. A non-base64 value raised `binascii.Error`, aborting seed
generation.

**Fix:** wrap the decode in `try/except (binascii.Error, ValueError,
UnicodeDecodeError)` and fall back to the raw value for the log line.

### 8 — Loose dependency constraints (Low/Med)

Security-relevant packages were pinned to `*`. Tightened to caret ranges anchored
to the already-locked versions (no resolution change): `quart ^0.19`,
`authlib ^1.6`, `aiohttp ^3.10`, `tortoise-orm ^0.21`, `PyYAML ^6.0`,
`werkzeug ^3.1`, `sentry-sdk ^2.18`.

### 9 — Unbounded `page` parameter (Low)

`page_size` was capped at 100 but `page` was unbounded, allowing huge offsets.
Clamped to `1 … 100000` in both paginated async-tournament endpoints.

### 10 — Dead vendored frontend assets (Low)

`static/theme-assets/` (42 MB, including `jquery-1.12.3` with known XSS CVEs) and
`static/assets/` were legacy Chameleon/Jinja assets. There are no remaining
`render_template` calls or Jinja templates, and nothing — backend or SPA —
references them; the Vite SPA in `presentation/api/spa/` is the build pipeline.

**Fix:** deleted both trees and removed the now-dead `/assets/<path>` and
`/theme-assets/<path>` routes (and their reserved prefixes). The frontend is built
with `npm install && npm run build`; assets are no longer vendored.

## Reviewed & accepted (not a vulnerability)

- **Async-tournament leaderboard exposes `discord_user_id` / `rtgg_id` /
  `twitch_name` for inactive tournaments** (`blueprints/asynctournament.py`). The
  maintainer confirmed these identifiers are **public information** by design.
  Inactive-tournament leaderboards/pools/player pages are intentionally public.
  No change.

## Explicitly refuted (do not "fix")

- **Cross-tournament IDOR on race/review endpoints.** Refuted — every repository
  lookup is scoped by `tournament=tournament`
  (`repositories/async_tournament_repository.py`: `get_race`, `get_race_for_review`,
  `get_user_race`, `list_tournament_user_races`), so a `race_id` from another
  tournament resolves to `None`.
- **"Session cookie missing HttpOnly."** Incorrect — Quart sets `HttpOnly` by
  default; only `Secure`/`SameSite` were the real gaps (Finding 1).
- **Discord OAuth missing `state`/CSRF.** Already implemented correctly in
  `oauth_client.py` (state generated at `create_session`, validated in `callback`).

## Clean areas (verified, no findings)

- SQL injection — Tortoise ORM only; no raw SQL or string-formatted queries.
- Command injection — `create_subprocess_exec` with arg lists; no `shell=True`,
  `os.system`, `eval`, or `exec`.
- Deserialization — `yaml.safe_load` throughout; no `pickle`/`yaml.load`.
- SSRF — outbound URLs are hardcoded or config-sourced, not user-controlled.
- Path traversal — `safe_join` / `send_from_directory` for static serving;
  `os.path.basename` on preset names.
