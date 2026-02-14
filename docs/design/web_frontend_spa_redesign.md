# Web Frontend SPA Redesign — Architecture & API Contract

> Last updated: 2026-02-13
> Status: **Design** — awaiting owner confirmation on open questions

## 1. Problem Statement

The current web frontend (`alttprbot_api/`) is a server-rendered Jinja2 application built on the **Chameleon Admin Template** (Bootstrap 4 Lite) — a purchased admin dashboard theme. Key problems:

| Issue | Detail |
|-------|--------|
| **Non-responsive layout** | The Chameleon theme uses a fixed vertical sidebar + fixed navbar that collapses poorly on mobile. All page content is laid out with Bootstrap 4 grid but none of the templates use responsive breakpoints meaningfully. |
| **Desktop-only sidebar navigation** | The sidebar disappears on small screens via a CSS animation toggle that requires JavaScript; no mobile-first mobile menu exists. |
| **Dead theme weight** |~40+ vendor JS plugins, 500+ CSS files, fonts, images, and chart libraries are shipped but most are unused (weather icons, gallery, sliders, editors, animation, calendar, timeline, etc.). |
| **Tight server coupling** | Every page navigation triggers a full server round-trip; no client-side routing, no optimistic UI, no loading states. |
| **Inline logic in templates** | Business logic (permission checks, conditional rendering, pagination math) is embedded in Jinja2 templates, making them hard to test. |
| **No component reuse** | Each template rebuilds tables, forms, and cards from scratch using raw HTML + Bootstrap utility classes. |
| **Stale theme metadata** | The base template still contains meta descriptions for "Chameleon Admin" and links to the theme vendor's purchase page. |

## 2. Decision Record

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Frontend framework | **React 18** + React Router v6 + TanStack Query v5 | Largest ecosystem, strongest community tooling, owner preference |
| Build toolchain | **Vite** | Fast dev server, native ESM, excellent React/TS support |
| Styling | **Tailwind CSS v3** | Utility-first, mobile-first by default, small production bundles via purge |
| Language | **TypeScript** | Type-safe API contracts, better refactoring confidence |
| Deployment | **Quart serves built SPA** as static files — no infra changes | Single-process architecture preserved; SPA assets served from a catch-all route |
| Auth model | **Server-side OAuth session** (unchanged) | Quart handles Discord OAuth redirect + session cookie; SPA calls `/api/me` to get current user |
| Migration strategy | **Clean-break replacement** | All Jinja2 templates, Chameleon theme assets, and server-rendered HTML routes removed in one release |

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                     Browser                         │
│  ┌───────────────────────────────────────────────┐  │
│  │           React SPA (Vite build)              │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────┐  │  │
│  │  │  Router   │ │  Queries │ │   Tailwind   │  │  │
│  │  │(React     │ │(TanStack │ │   (utility   │  │  │
│  │  │ Router v6)│ │ Query v5)│ │    CSS)      │  │  │
│  │  └──────────┘ └──────────┘ └──────────────┘  │  │
│  └──────────────────┬────────────────────────────┘  │
│                     │  fetch() / JSON               │
└─────────────────────┼───────────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────────┐
│            Quart Backend (unchanged core)            │
│                     │                                │
│  ┌──────────────────▼─────────────────────────────┐ │
│  │  /api/*  JSON endpoints (existing + new)       │ │
│  ├────────────────────────────────────────────────┤ │
│  │  /login/, /callback/discord/, /logout/         │ │
│  │  (server-side OAuth — redirects, no HTML)      │ │
│  ├────────────────────────────────────────────────┤ │
│  │  /*  catch-all → serve SPA index.html          │ │
│  │  /assets/*  → serve Vite build output          │ │
│  └────────────────────────────────────────────────┘ │
│                     │                                │
│            Tortoise ORM / MySQL                      │
└─────────────────────────────────────────────────────┘
```

### SPA Serving Strategy

Quart already has static file serving via `send_from_directory`. The new approach:

1. Vite builds the SPA into `alttprbot_api/spa/dist/`.
2. A new Quart catch-all route serves `index.html` for any non-API, non-auth path (client-side routing).
3. Vite-hashed asset files (`/assets/js/*, /assets/css/*`) are served from the same dist directory.
4. The existing `/api/*` routes remain unchanged and return JSON.
5. The OAuth routes (`/login/`, `/callback/discord/`, `/logout/`) remain server-side redirects.

## 4. API Contract

The SPA requires a clean JSON API surface. Some endpoints already exist; others need to be created by converting current template-rendering routes to JSON-only responses.

### 4.1 Auth & User Endpoints

| Method | Path | Auth | Response | Notes |
|--------|------|------|----------|-------|
| GET | `/api/me` | Session cookie | `{ user: { id, name, avatar_url } }` or `401` | **New.** Replaces `discord.fetch_user()` calls scattered across templates. |
| GET | `/login/` | None | `302` → Discord OAuth | Unchanged. SPA navigates here via `window.location`. |
| GET | `/callback/discord/` | None | `302` → SPA route | Unchanged. Redirect target becomes SPA path instead of `/me/`. |
| GET | `/logout/` | None | `302` → `/` | Unchanged. Clears session. |
| POST | `/api/purgeme` | Session | `{ success: true }` | **New.** Replaces form POST + redirect. |

### 4.2 Presets Endpoints

| Method | Path | Auth | Response | Status |
|--------|------|------|----------|--------|
| GET | `/api/presets/namespaces` | None | `[{ id, name, discord_user_id, display_name }]` | **New.** |
| GET | `/api/presets/namespaces/<ns>` | None | `{ namespace, presets: [{ randomizer, preset_name, content }] }` | **New.** |
| GET | `/api/presets/namespaces/<ns>/<rand>/<preset>` | None | `{ preset_name, randomizer, content (YAML string) }` | **New.** |
| POST | `/api/presets/namespaces/<ns>/<rand>` | Session + ownership | `{ success, preset_name }` | **New.** Create preset. |
| PUT | `/api/presets/namespaces/<ns>/<rand>/<preset>` | Session + ownership | `{ success }` | **New.** Update preset. |
| DELETE | `/api/presets/namespaces/<ns>/<rand>/<preset>` | Session + ownership | `{ success }` | **New.** |
| GET | `/api/presets/<rand>/list` | None | Existing JSON endpoint | Existing. |
| GET | `/api/presets/<rand>` | None | Existing JSON endpoint | Existing. |
| GET | `/presets/download/<ns>/<rand>/<preset>` | None | YAML file download | Existing. Keep as-is. |

### 4.3 Async Tournament Endpoints

All existing `/async/api/*` endpoints are already JSON and require API key auth — **unchanged**.

For the HTML views that are currently template-rendered, new JSON endpoints are needed:

| Method | Path | Auth | Response | Status |
|--------|------|------|----------|--------|
| GET | `/api/async/dashboard/<id>` | Session | `{ tournament, player, races, reattempted }` | **New.** |
| GET | `/api/async/reattempt/<id>` | Session | `{ tournament, player, race }` | **New.** |
| POST | `/api/async/reattempt/<id>` | Session | `{ success }` | **New.** |
| GET | `/api/async/queue/<id>` | Session + permission | `{ tournament, races, pagination }` | **New.** |
| GET | `/api/async/review/<id>/<race_id>` | Session + permission | `{ tournament, race, already_claimed, reviewable }` | **New.** |
| POST | `/api/async/review/<id>/<race_id>` | Session + permission | `{ success }` | **New.** |
| GET | `/api/async/leaderboard/<id>` | Optional session | `{ tournament, leaderboard, estimate, sort_key }` | **New.** |
| GET | `/api/async/player/<id>/<user_id>` | Optional session | `{ tournament, player, races }` | **New.** |
| GET | `/api/async/pools/<id>` | Optional session | `{ tournament, pools }` | **New.** |
| GET | `/api/async/permalink/<id>/<pid>` | Optional session | `{ tournament, permalink, races }` | **New.** |

### 4.4 Tournament Submission Endpoints

| Method | Path | Auth | Response | Status |
|--------|------|------|----------|--------|
| GET | `/api/tournament/games` | None | Existing JSON | Existing. |
| GET | `/api/tournament/submit/<event>` | Session | `{ event, settings_list, episode_id, form_type }` | **New.** Returns form metadata. |
| POST | `/api/tournament/submit` | Session | `{ success, tournament_race }` | **New.** |

### 4.5 Other Endpoints

| Method | Path | Auth | Response | Status |
|--------|------|------|----------|--------|
| GET | `/api/sglive/dashboard` | None | `{ games: [...] }` | **New.** |
| GET | `/api/sglive/reports/capacity` | None | `{ events, report, alert_threshold }` | **New.** |
| GET | `/api/ranked_choice/<id>` | Session + role | `{ election, already_voted, votes? }` | **New.** |
| POST | `/api/ranked_choice/<id>` | Session + role | `{ success }` | **New.** |
| GET | `/api/triforcetexts/<pool>` | Session | `{ pool_name, author_name_field }` | **New.** |
| POST | `/api/triforcetexts/<pool>/submit` | Session | `{ success }` | **New.** |
| GET | `/api/triforcetexts/<pool>/moderation` | Session + moderator | `{ pool_name, texts: [...] }` | **New.** |
| POST | `/api/triforcetexts/<pool>/moderation/<id>/<action>` | Session + moderator | `{ success }` | **New.** |
| POST | `/api/racetime/cmd` | API key (query param) | Existing JSON | Existing. |
| GET | `/racetime/verification/initiate` | Session | `302` redirect | Existing. Keep. |
| GET | `/racetime/verify/return` | Session | `{ success, racetime_name }` | **Convert.** |
| POST | `/api/settingsgen/mystery` | None | Existing JSON | Existing. |
| GET | `/api/settingsgen/mystery` | None | Existing JSON | Existing. |
| GET | `/healthcheck` | None | Existing JSON | Existing. |

### 4.6 API Response Conventions

All new JSON endpoints follow a consistent envelope:

```jsonc
// Success
{ "data": { ... }, "error": null }

// Error
{ "data": null, "error": { "code": "UNAUTHORIZED", "message": "..." } }
```

HTTP status codes convey the result; the envelope provides structured detail.

## 5. SPA Route Map

React Router v6 routes mapped to current page functionality:

| SPA Route | Component | Data Source | Auth |
|-----------|-----------|-------------|------|
| `/` | `HomePage` | Static | No |
| `/presets` | `PresetsListPage` | `GET /api/presets/namespaces` | No |
| `/presets/:ns` | `PresetNamespacePage` | `GET /api/presets/namespaces/:ns` | No |
| `/presets/:ns/:rand/:preset` | `PresetViewPage` | `GET /api/presets/namespaces/:ns/:rand/:preset` | No |
| `/presets/:ns/create` | `PresetCreatePage` | — | Yes |
| `/me` | `ProfilePage` | `GET /api/me` | Yes |
| `/async/races/:id` | `AsyncTournamentDashboard` | `GET /api/async/dashboard/:id` | Yes |
| `/async/races/:id/reattempt` | `AsyncReattemptPage` | `GET /api/async/reattempt/:id` | Yes |
| `/async/races/:id/queue` | `AsyncQueuePage` | `GET /api/async/queue/:id` | Yes + perm |
| `/async/races/:id/review/:raceId` | `AsyncReviewPage` | `GET /api/async/review/:id/:raceId` | Yes + perm |
| `/async/races/:id/leaderboard` | `AsyncLeaderboardPage` | `GET /api/async/leaderboard/:id` | Optional |
| `/async/player/:id/:userId` | `AsyncPlayerPage` | `GET /api/async/player/:id/:userId` | Optional |
| `/async/pools/:id` | `AsyncPoolsPage` | `GET /api/async/pools/:id` | Optional |
| `/async/permalink/:id/:pid` | `AsyncPermalinkPage` | `GET /api/async/permalink/:id/:pid` | Optional |
| `/submit/:event` | `TournamentSubmitPage` | `GET /api/tournament/submit/:event` | Yes |
| `/sglive` | `SGLiveDashboard` | `GET /api/sglive/dashboard` | No |
| `/sglive/reports/capacity` | `SGLiveCapacityReport` | `GET /api/sglive/reports/capacity` | No |
| `/ranked_choice/:id` | `RankedChoicePage` | `GET /api/ranked_choice/:id` | Yes |
| `/triforcetexts/:pool` | `TriforceTextsPage` | `GET /api/triforcetexts/:pool` | Yes |
| `/triforcetexts/:pool/moderation` | `TriforceTextsModerationPage` | `GET /api/triforcetexts/:pool/moderation` | Yes + mod |
| `/racetime/verified` | `RaceTimeVerifiedPage` | Query params | Yes |
| `*` | `NotFoundPage` | — | No |

## 6. Component Architecture

```
src/
├── main.tsx                    # ReactDOM.createRoot + RouterProvider
├── router.tsx                  # Route definitions
├── api/                        # API client layer
│   ├── client.ts               # fetch wrapper (cookie auth, error handling)
│   ├── queries/                # TanStack Query hooks per domain
│   │   ├── useAuth.ts          # useCurrentUser, useLogout
│   │   ├── usePresets.ts       # useNamespaces, usePreset, useMutatePreset
│   │   ├── useTournament.ts    # useDashboard, useLeaderboard, etc.
│   │   └── ...
│   └── types.ts                # TypeScript interfaces matching API contract
├── components/                 # Reusable UI components
│   ├── layout/
│   │   ├── AppShell.tsx        # Top nav + mobile drawer + content area
│   │   ├── Navbar.tsx          # Responsive top bar with user menu
│   │   ├── MobileDrawer.tsx    # Slide-out nav for mobile
│   │   └── Footer.tsx
│   ├── ui/                     # Primitives
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Table.tsx
│   │   ├── Badge.tsx
│   │   ├── LoadingSkeleton.tsx
│   │   ├── ErrorBoundary.tsx
│   │   └── ...
│   └── domain/                 # Domain-specific composites
│       ├── PresetCard.tsx
│       ├── LeaderboardTable.tsx
│       ├── RaceStatusBadge.tsx
│       └── ...
├── pages/                      # Route-level page components
│   ├── HomePage.tsx
│   ├── ProfilePage.tsx
│   ├── presets/
│   │   ├── PresetsListPage.tsx
│   │   ├── PresetNamespacePage.tsx
│   │   ├── PresetViewPage.tsx
│   │   └── PresetCreatePage.tsx
│   ├── async-tournament/
│   │   ├── AsyncTournamentDashboard.tsx
│   │   ├── AsyncLeaderboardPage.tsx
│   │   └── ...
│   ├── tournament/
│   │   └── TournamentSubmitPage.tsx
│   ├── sglive/
│   │   ├── SGLiveDashboard.tsx
│   │   └── SGLiveCapacityReport.tsx
│   └── ...
├── hooks/                      # Shared custom hooks
│   ├── useAuth.ts              # Auth context + redirect helper
│   └── useMediaQuery.ts        # Responsive breakpoint hook
├── context/
│   └── AuthContext.tsx          # React context for current user state
└── styles/
    └── tailwind.css             # Tailwind directives + any custom utilities
```

## 7. Responsive Design Strategy

### Breakpoints (Tailwind defaults)

| Breakpoint | Min width | Target |
|------------|-----------|--------|
| `sm` | 640px | Large phones landscape |
| `md` | 768px | Tablets |
| `lg` | 1024px | Small laptops |
| `xl` | 1280px | Desktop |

### Layout Behavior

| Viewport | Navigation | Content |
|----------|-----------|---------|
| < `md` | **Top navbar** with hamburger → slide-out drawer | Full-width single column |
| ≥ `md` | **Top navbar** with inline nav links | Centered max-width container |

The fixed vertical sidebar is **eliminated entirely**. All navigation moves to a responsive top navbar with a collapsible mobile drawer, matching modern web app conventions.

### Key Responsive Patterns

- **Tables** → Horizontally scrollable on mobile, or collapsed into card-list view for leaderboards/race queues.
- **Forms** → Single-column stacked layout on mobile; optional two-column on desktop.
- **Cards** → CSS Grid with `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` for preset listings and dashboards.
- **Typography** → Tailwind's responsive text utilities (`text-sm md:text-base`) for readability scaling.

## 8. Files to Remove (Clean Break)

Everything below is deleted when the SPA ships:

```
alttprbot_api/templates/           # All 35 Jinja2 templates
alttprbot_api/static/theme-assets/ # Entire Chameleon theme (~500+ files)
alttprbot_api/static/assets/scss/  # Custom SCSS (replaced by Tailwind)
alttprbot_api/static/assets/js/    # Custom JS (replaced by React)
```

Retained:
- `alttprbot_api/static/assets/images/sahasrahbot_transparent.png` → moved into SPA `public/` directory.
- All blueprint Python files (refactored to return JSON instead of `render_template`).
- `alttprbot_api/api.py` (refactored: template routes become API routes, catch-all added for SPA).
- `alttprbot_api/auth.py` (unchanged).
- `alttprbot_api/oauth_client.py` (unchanged).

## 9. Backend Changes Required

### 9.1 New Catch-All Route

```python
# In api.py — after all /api/* and auth routes
@sahasrahbotapi.route('/', defaults={'path': ''})
@sahasrahbotapi.route('/<path:path>')
async def serve_spa(path):
    # Serve static assets if they exist
    spa_dir = os.path.join(os.path.dirname(__file__), 'spa', 'dist')
    file_path = os.path.join(spa_dir, path)
    if path and os.path.isfile(file_path):
        return await send_from_directory(spa_dir, path)
    # Otherwise serve index.html for client-side routing
    return await send_from_directory(spa_dir, 'index.html')
```

### 9.2 Blueprint Refactoring Pattern

Each blueprint that currently calls `render_template()` gets a parallel `/api/` route returning JSON:

```python
# Before (removed)
@bp.route('/presets')
async def all_presets():
    namespaces = await models.PresetNamespaces.all()
    return await render_template('preset_namespaces_all.html', ...)

# After
@bp.route('/api/presets/namespaces')
async def api_all_presets():
    namespaces = await models.PresetNamespaces.all()
    return jsonify(data=[ns.to_dict() for ns in namespaces])
```

### 9.3 New `/api/me` Endpoint

```python
@sahasrahbotapi.route('/api/me')
async def api_me():
    try:
        user = await discord.fetch_user()
        return jsonify(data={"id": user.id, "name": user.name, "avatar_url": user.avatar_url})
    except Unauthorized:
        return jsonify(data=None, error={"code": "UNAUTHORIZED"}), 401
```

### 9.4 OAuth Redirect Target Update

The `/callback/discord/` handler's redirect target changes from `/me/` to `/me` (SPA route — no trailing slash requirement, but functionally the same since the SPA router handles both).

## 10. Open Questions for Owner

1. **Brand identity**: Should the SPA keep the existing SahasrahBot logo and color palette, or is this an opportunity for a visual refresh?
2. **Dark mode**: Should the new UI support a dark mode toggle? (Tailwind makes this straightforward with `dark:` variants.)
3. **SG Live seed generation links**: The current SG Live dashboard has direct `<a>` links to `/sglive/generate/alttpr` etc. that redirect to external seed URLs. Should these remain as server-side redirects, or should the SPA call an API and display the result inline?
4. **Schedule & User blueprints**: These are currently DEBUG-only stubs. Should they be included in the new SPA scope or deferred?
