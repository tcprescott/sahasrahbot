# SPA Remaining Pages — Agent Handoff

> Written 2026-06-12. Covers every page in the route map that is not yet implemented.
> Intended to be handed to parallel agents; each section is self-contained.

---

## 0. Current State

### Implemented (do not re-implement)
| Route | Component |
|---|---|
| `/` | `HomePage` |
| `/presets` | `PresetsListPage` |
| `/async/leaderboard/:id` | `AsyncLeaderboardPage` |
| `/async/races/:id` | `AsyncDashboardPage` |
| `/async/player/:tid/:uid` | `AsyncPlayerPage` |
| `/submit/:event` | `TournamentSubmitPage` |
| `/me` | `ProfilePage` |
| `/racetime/verified` | `RaceTimeVerifiedPage` |

### Not yet implemented (this doc)
- `/async/races/:id/reattempt` — Reattempt page
- `/async/races/:id/queue` — Admin queue
- `/async/races/:id/review/:raceId` — Admin review
- `/async/pools/:id` — Pools view
- `/async/permalink/:id/:pid` — Permalink view
- `/triforcetexts/:pool` — Triforce text submission
- `/triforcetexts/:pool/moderation` — Triforce text moderation
- `/ranked_choice/:id` — Ranked choice ballot
- `/sglive` — SG Live dashboard

---

## 1. Design System Reference

Read these files before writing any component:

- **`alttprbot_api/spa/src/pages/async-tournament/AsyncLeaderboardPage.tsx`** — canonical page template (pagehead → block → panel pattern)
- **`alttprbot_api/spa/src/styles/leaderboard.css`** — canonical CSS (variables, skel, panel, badge)
- **`alttprbot_api/spa/src/pages/tournament/TournamentSubmitPage.tsx`** — form page with auth gating, state machine, POST submission
- **`alttprbot_api/spa/src/styles/submit.css`** — form styles (field, control, label, alert-error/success, spinner, btn)
- **`alttprbot_api/spa/src/components/ui/Badge.tsx`** — `<Badge tone="gold|teal|crimson|default" dot>label</Badge>`
- **`alttprbot_api/spa/src/styles/tokens.css`** — all CSS variables

### Key design conventions
- **Typography**: `font-family: 'Cinzel Decorative'` for headings (already set on `.sb-title`/`h1`/`h2`), `'Hanken Grotesk'` body, `'Space Mono'` for times/numbers/code
- **Theming**: `[data-theme="dark"]` / `[data-theme="light"]` on `<html>`. Use CSS variables only — no Tailwind `dark:` variants
- **Page structure**:
  ```html
  <section className="pagehead">
    <div className="glow" /><div className="grid" /><div className="wrap">
      <!-- breadcrumb nav.crumb, h1.sb-title, badges -->
    </div>
  </section>
  <section className="block"><div className="wrap">
    <!-- panels -->
  </div></section>
  ```
- **Panels**: `<div className="panel"><div className="panel-head"><h3>…</h3></div><div className="panel-body">…</div></div>`
- **Loading**: `<div className="skel" style={{width: X, height: Y, borderRadius: Z}} />` — shimmer animation defined in `tokens.css`
- **Alerts**: `<div className="alert alert-error|alert-success"><span className="alert-icon">⚠|✓</span><p>…</p></div>`
- **Buttons**: `<button className="btn btn-primary|btn-ghost|btn-sm">…</button>`
- **Scroll reveal**: Add `className="onscroll"` to panels; `AppShell` handles IntersectionObserver. `reveal d1/d2/d3` for immediate staggered entry (no IO needed)
- **Auth pattern**: Always fetch from a JSON endpoint; if 401 → show auth prompt panel with `<a href="/login/">Sign in with Discord →</a>`; if 403 → show "access denied" panel
- **Fetch pattern**: plain `fetch()` in `useCallback` + `useEffect`, state machine with `useState`. No TanStack Query.
- **No trailing slashes** in SPA `<Link>` `to` props

### Backend API conventions (established patterns)
- New session-auth JSON endpoints follow the `leaderboard.json` / `dashboard.json` pattern
- Import `Unauthorized` from `alttprbot_api.oauth_client` (already imported at top of `asynctournament.py`)
- Import `checks` is already at top of `asynctournament.py`
- `jsonify` is already imported
- Error responses: `jsonify({'error': 'message'}), 4XX`
- Datetimes: `.isoformat()` if not None
- Model computed properties: `race.elapsed_time_formatted`, `race.score_formatted`

---

## 2. Router & Build

After creating page components, add them to **`alttprbot_api/spa/src/router.tsx`**:

```typescript
import { MyNewPage } from './pages/MyNewPage';
// inside children array:
{ path: '/my/route/:param', element: <MyNewPage /> },
```

Build command (from `alttprbot_api/spa/`):
```bash
PATH="$HOME/.nvm/versions/node/v20.20.2/bin:$PATH" npm run build
```

Then restart with: `lsof -ti:5001 | xargs kill -9; sleep 1 && cd /path/to/sahasrahbot && poetry run python sahasrahbot.py > /tmp/sahasrahbot.log 2>&1 &`

**Important**: When you remove a Jinja GET route from a blueprint, also check `_RESERVED_PREFIXES` in `alttprbot_api/api.py` — if the path prefix is listed there, remove it so the SPA catch-all can serve the new route.

---

## 3. `/async/races/:id/reattempt` — Reattempt Page

**Purpose**: A player requests a reattempt on one of their finished runs. One-time action per tournament.

**Auth**: Required (redirect to login if not authenticated).

### 3.1 Existing Jinja GET route to replace

`alttprbot_api/blueprints/asynctournament.py`, `async_tournament_reattempt`:
- Takes `?race_id=X` query param
- Validates: user hasn't already reattempted, race belongs to this user in this tournament
- Returns 403 if already reattempted

**Remove this route** when the SPA page is built — the SPA calls the `.json` endpoint below instead.

### 3.2 New backend JSON endpoint

Add to `asynctournament.py` **before** the existing `async_tournament_reattempt_submit` POST route:

```python
@asynctournament_blueprint.route('/races/<int:tournament_id>/reattempt.json', methods=['GET'])
async def async_tournament_reattempt_json(tournament_id: int):
    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        return jsonify({'error': 'Authentication required.'}), 401

    user = await models.Users.get_or_none(discord_user_id=discord_user.id)
    if user is None:
        return jsonify({'error': 'Authentication required.'}), 401

    tournament = await models.AsyncTournament.get_or_none(id=tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'}), 404

    race_id = request.args.get('race_id', None)
    if race_id is None:
        return jsonify({'error': 'race_id is required.'}), 400

    reattempted_races = await models.AsyncTournamentRace.filter(user=user, tournament=tournament, reattempted=True)
    if reattempted_races:
        return jsonify({'error': 'You have already reattempted a race in this tournament.'}), 403

    race = await models.AsyncTournamentRace.get_or_none(id=int(race_id), user=user, tournament=tournament)
    if race is None:
        return jsonify({'error': 'Race not found or you are not the player.'}), 403

    await race.fetch_related('permalink', 'permalink__pool')

    return jsonify({
        'tournament': {'id': tournament.id, 'name': tournament.name, 'active': tournament.active},
        'race': {
            'id': race.id,
            'status': race.status,
            'elapsed_time': race.elapsed_time_formatted,
            'pool_name': race.permalink.pool.name,
            'permalink_url': race.permalink.url,
        },
    })
```

The **existing POST** at `POST /race/<tournament_id>/reattempt` (note: singular `race`) can stay as-is — it already takes form data. The SPA should POST to it as `application/x-www-form-urlencoded` with `reason=<text>` and `?race_id=X`. On success it redirects (302) to the Jinja dashboard — ignore the redirect; navigate client-side to `/async/races/:id` instead.

Alternatively, add a new JSON POST:

```python
@asynctournament_blueprint.route('/races/<int:tournament_id>/reattempt.json', methods=['POST'])
async def async_tournament_reattempt_submit_json(tournament_id: int):
    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        return jsonify({'error': 'Authentication required.'}), 401

    user = await models.Users.get_or_none(discord_user_id=discord_user.id)
    if user is None:
        return jsonify({'error': 'Authentication required.'}), 401

    tournament = await models.AsyncTournament.get_or_none(id=tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'}), 404

    reattempted_races = await models.AsyncTournamentRace.filter(user=user, tournament=tournament, reattempted=True)
    if reattempted_races:
        return jsonify({'error': 'Already reattempted.'}), 403

    payload = await request.get_json(force=True) or {}
    race_id = payload.get('race_id')
    reason = payload.get('reason', '')

    if not race_id:
        return jsonify({'error': 'race_id is required.'}), 400

    race = await models.AsyncTournamentRace.get_or_none(id=int(race_id), user=user, tournament=tournament)
    if race is None:
        return jsonify({'error': 'Race not found or you are not the player.'}), 403

    race.reattempted = True
    race.reattempt_reason = reason
    await race.save()

    return jsonify({'success': True})
```

### 3.3 Frontend component

File: `alttprbot_api/spa/src/pages/async-tournament/AsyncReattemptPage.tsx`
CSS: `alttprbot_api/spa/src/styles/reattempt.css` (or reuse `submit.css`)

- Reads `:id` from `useParams`, reads `?race_id=X` from `useSearchParams`
- Page head: "REATTEMPT REQUEST" h1, breadcrumb (Home / Async Tournament / Dashboard / Reattempt), badges: tournament name (gold)
- State machine: loading → 401 (auth prompt) → 403 (already reattempted panel) → 400 (missing race_id) → error → ready
- **Ready state**: a confirmation panel showing:
  - The race being reattempted: pool name, time, permalink URL
  - Warning box: "This action cannot be undone. You are allowed one reattempt per tournament." (crimson alert)
  - A textarea for the reattempt reason (label: "Reason for reattempt")
  - Submit button → POST to `/async/races/:id/reattempt.json` with `{race_id, reason}`
  - On success: navigate to `/async/races/:id`
- **Already reattempted state**: gold info panel "You have already used your reattempt for this tournament."

---

## 4. `/async/races/:id/queue` — Admin Queue

**Purpose**: Admin/mod view of all race submissions for a tournament, with pagination and filters.

**Auth**: Required, admin/mod only (403 for others).

### 4.1 Existing Jinja GET route to replace

`asynctournament.py`, `async_tournament_queue` — supports query filters: `status`, `reviewed`, `review_status`, `live`, `page`. **Remove this route** when done.

### 4.2 New backend JSON endpoint

Add to `asynctournament.py`:

```python
@asynctournament_blueprint.route('/races/<int:tournament_id>/queue.json', methods=['GET'])
async def async_tournament_queue_json(tournament_id: int):
    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        return jsonify({'error': 'Authentication required.'}), 401

    user = await models.Users.get_or_none(discord_user_id=discord_user.id)
    if user is None:
        return jsonify({'error': 'Authentication required.'}), 401

    tournament = await models.AsyncTournament.get_or_none(id=tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'}), 404

    authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod'])
    if not authorized:
        return jsonify({'error': 'Not authorized.'}), 403

    page = int(request.args.get('page', 1))
    page_size = 20
    request_filter = {}

    status = request.args.get('status', 'finished')
    if status != 'all':
        request_filter['status'] = status

    reviewer = request.args.get('reviewed', 'all')
    if reviewer == 'unreviewed':
        request_filter['reviewed_by'] = None
    elif reviewer == 'me':
        request_filter['reviewed_by'] = user
    elif reviewer != 'all':
        try:
            request_filter['reviewed_by_id'] = int(reviewer)
        except ValueError:
            pass

    review_status = request.args.get('review_status', 'pending')
    if review_status != 'all':
        request_filter['review_status'] = review_status

    live = request.args.get('live', 'false')
    if live != 'all':
        request_filter['thread_id__isnull'] = live == 'true'

    races = await tournament.races.filter(
        reattempted=False, **request_filter
    ).offset((page - 1) * page_size).limit(page_size).prefetch_related(
        'user', 'reviewed_by', 'permalink', 'permalink__pool'
    )

    return jsonify({
        'tournament': {'id': tournament.id, 'name': tournament.name, 'active': tournament.active},
        'races': [
            {
                'id': race.id,
                'status': race.status,
                'review_status': race.review_status,
                'elapsed_time': race.elapsed_time_formatted,
                'score_formatted': race.score_formatted,
                'created': race.created.isoformat() if race.created else None,
                'pool_name': race.permalink.pool.name,
                'permalink_url': race.permalink.url,
                'user_id': race.user.id,
                'user_display_name': race.user.display_name,
                'reviewed_by_name': race.reviewed_by.display_name if race.reviewed_by else None,
                'runner_vod_url': race.runner_vod_url,
            }
            for race in races
        ],
        'page': page,
        'page_size': page_size,
        'filters': {'status': status, 'reviewed': reviewer, 'review_status': review_status, 'live': live},
    })
```

### 4.3 Frontend component

File: `alttprbot_api/spa/src/pages/async-tournament/AsyncQueuePage.tsx`

- Page head: "REVIEW QUEUE" h1, breadcrumb (Home / Async Tournament / Queue), badges: tournament name (gold), "ADMIN" badge (crimson)
- Filter bar above the table: dropdowns for Status / Review Status / Reviewed By / Live-only toggle. Changing a filter updates URL search params (`useSearchParams`) and re-fetches.
- Runs table: Player | Pool | Time | Score | Review Status | Reviewer | VoD | Actions
  - Each row links to `/async/races/:id/review/:raceId` for the review action
  - Player name links to `/async/player/:id/:userId`
  - VoD: external link icon if present
- Pagination: Prev / Next buttons, shows "Page N"
- Empty state: "No runs match the current filters."
- 403 state: "Admin or moderator access required."
- Loading: skeleton rows

---

## 5. `/async/races/:id/review/:raceId` — Admin Review

**Purpose**: Admin/mod reviews a single race submission. Claims it for review, then approves or rejects.

**Auth**: Required, admin/mod only.

### 5.1 Existing routes to reference

`asynctournament.py`, `async_tournament_review` (GET) and `async_tournament_review_submit` (POST).

**Remove the GET route** when done. Keep the **POST route** as-is (it accepts form data and redirects) OR add a new JSON POST endpoint:

```python
@asynctournament_blueprint.route('/races/<int:tournament_id>/review/<int:race_id>/data.json', methods=['GET'])
async def async_tournament_review_json(tournament_id: int, race_id: int):
    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        return jsonify({'error': 'Authentication required.'}), 401

    user = await models.Users.get_or_none(discord_user_id=discord_user.id)
    if user is None:
        return jsonify({'error': 'Authentication required.'}), 401

    tournament = await models.AsyncTournament.get_or_none(id=tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'}), 404

    authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod'])
    if not authorized:
        return jsonify({'error': 'Not authorized.'}), 403

    race = await models.AsyncTournamentRace.get_or_none(id=race_id, tournament=tournament)
    if race is None:
        return jsonify({'error': 'Race not found.'}), 404

    reviewable = race.status == 'finished' and not race.reattempted

    await race.fetch_related('user', 'reviewed_by', 'permalink', 'permalink__pool', 'live_race')

    # Auto-claim for review (same as Jinja route)
    if race.reviewed_by is None and reviewable:
        race.reviewed_by = user
        await race.save()

    return jsonify({
        'tournament': {'id': tournament.id, 'name': tournament.name},
        'race': {
            'id': race.id,
            'status': race.status,
            'review_status': race.review_status,
            'elapsed_time': race.elapsed_time_formatted,
            'score_formatted': race.score_formatted,
            'created': race.created.isoformat() if race.created else None,
            'start_time': race.start_time.isoformat() if race.start_time else None,
            'end_time': race.end_time.isoformat() if race.end_time else None,
            'runner_notes': race.runner_notes,
            'runner_vod_url': race.runner_vod_url,
            'run_collection_rate': race.run_collection_rate,
            'run_igt': race.run_igt,
            'reattempted': race.reattempted,
            'reviewer_notes': race.reviewer_notes,
            'reviewed_by_name': race.reviewed_by.display_name if race.reviewed_by else None,
            'reviewed_at': race.reviewed_at.isoformat() if race.reviewed_at else None,
            'pool_name': race.permalink.pool.name,
            'permalink_url': race.permalink.url,
            'permalink_notes': race.permalink.notes,
            'user_id': race.user.id,
            'user_display_name': race.user.display_name,
        },
        'reviewable': reviewable,
        'already_claimed': race.reviewed_by is not None and race.reviewed_by.id != user.id,
        'reviewer_is_self': race.user.id == user.id,
    })


@asynctournament_blueprint.route('/races/<int:tournament_id>/review/<int:race_id>/submit.json', methods=['POST'])
async def async_tournament_review_submit_json(tournament_id: int, race_id: int):
    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        return jsonify({'error': 'Authentication required.'}), 401

    user = await models.Users.get_or_none(discord_user_id=discord_user.id)
    if user is None:
        return jsonify({'error': 'Authentication required.'}), 401

    tournament = await models.AsyncTournament.get_or_none(id=tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'}), 404

    authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod'])
    if not authorized:
        return jsonify({'error': 'Not authorized.'}), 403

    race = await models.AsyncTournamentRace.get_or_none(id=race_id, tournament=tournament)
    if race is None:
        return jsonify({'error': 'Race not found.'}), 404

    if race.status != 'finished':
        return jsonify({'error': 'Race is not finished.'}), 400

    if race.reattempted:
        return jsonify({'error': 'Race was reattempted.'}), 400

    await race.fetch_related('user')
    if race.user.id == user.id:
        return jsonify({'error': 'Cannot review your own run.'}), 403

    payload = await request.get_json(force=True) or {}
    import datetime
    race.review_status = payload.get('review_status', 'pending')
    race.reviewer_notes = payload.get('reviewer_notes', None)
    race.reviewed_at = datetime.datetime.now()
    race.reviewed_by = user
    await race.save()

    return jsonify({'success': True})
```

### 5.2 Frontend component

File: `alttprbot_api/spa/src/pages/async-tournament/AsyncReviewPage.tsx`

- Page head: "RACE REVIEW" h1, breadcrumb (Home / Async Tournament / Queue / Review), badges: player name (gold), review status (teal/crimson/default)
- Two-column layout:
  - **Left**: race details panel — player, pool, time, score, VoD link, runner notes, collection rate, IGT, created/start/end times
  - **Right**: review form panel (if `reviewable`) OR read-only review status panel
- Review form (only when `reviewable && !already_claimed && !reviewer_is_self`):
  - `review_status` select: pending / approved / rejected
  - `reviewer_notes` textarea
  - Submit button → POST to `…/submit.json`
  - On success: navigate to `/async/races/:id/queue`
- If `already_claimed`: gold warning "This run is claimed by {reviewed_by_name}. You can still submit a review decision."
- If `reviewer_is_self`: crimson warning "You cannot review your own run."
- If not reviewable (status != finished, or reattempted): show reason as muted text

---

## 6. `/async/pools/:id` — Pools View

**Purpose**: Shows all permalink pools for a tournament and which permalinks are in each pool.

**Auth**: Optional; if tournament is active, requires admin/mod/public permission.

### 6.1 Existing Jinja GET route to replace

`asynctournament.py`, `async_tournament_pools`. **Remove this route** when done.

### 6.2 New backend JSON endpoint

```python
@asynctournament_blueprint.route('/pools/<int:tournament_id>/data.json', methods=['GET'])
async def async_tournament_pools_json(tournament_id: int):
    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        discord_user = None

    user = None
    if discord_user:
        user = await models.Users.get_or_none(discord_user_id=discord_user.id)

    tournament = await models.AsyncTournament.get_or_none(id=tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'}), 404

    authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod', 'public'])
    if not authorized and tournament.active:
        return jsonify({'error': 'Not authorized.'}), 403

    await tournament.fetch_related('permalink_pools', 'permalink_pools__permalinks')

    return jsonify({
        'tournament': {'id': tournament.id, 'name': tournament.name, 'active': tournament.active},
        'pools': [
            {
                'id': pool.id,
                'name': pool.name,
                'preset': pool.preset,
                'permalinks': [
                    {
                        'id': p.id,
                        'url': p.url,
                        'notes': p.notes,
                        'par_time': p.par_time_formatted if p.par_time else None,
                        'live_race': p.live_race,
                    }
                    for p in pool.permalinks
                ],
            }
            for pool in tournament.permalink_pools
        ],
    })
```

### 6.3 Frontend component

File: `alttprbot_api/spa/src/pages/async-tournament/AsyncPoolsPage.tsx`

- Page head: "POOLS" h1, breadcrumb (Home / Async Tournament / Pools), badges: tournament name (gold), LIVE/CLOSED status
- One card per pool (pool name as card header)
  - Table: Permalink URL (external link) | Notes | Par Time | Live Race (boolean badge)
- 403 state: tournament is active, access restricted
- Empty state: "No pools configured."

---

## 7. `/async/permalink/:id/:pid` — Permalink View

**Purpose**: Shows a specific permalink and all race results using it.

**Auth**: Optional; if tournament is active AND permalink is not a live_race, requires permission.

### 7.1 Existing Jinja GET route to replace

`asynctournament.py`, `async_tournament_permalink`. **Remove this route** when done.

Check the full implementation (around line 533) — it skips auth for live race permalinks.

### 7.2 New backend JSON endpoint

```python
@asynctournament_blueprint.route('/permalink/<int:tournament_id>/<int:permalink_id>/data.json', methods=['GET'])
async def async_tournament_permalink_json(tournament_id: int, permalink_id: int):
    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        discord_user = None

    user = None
    if discord_user:
        user = await models.Users.get_or_none(discord_user_id=discord_user.id)

    tournament = await models.AsyncTournament.get_or_none(id=tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'}), 404

    permalink = await models.AsyncTournamentPermalink.get_or_none(
        id=permalink_id, pool__tournament=tournament
    )
    if permalink is None:
        return jsonify({'error': 'Permalink not found.'}), 404

    if not permalink.live_race:
        authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod', 'public'])
        if not authorized and tournament.active:
            return jsonify({'error': 'Not authorized.'}), 403

    await permalink.fetch_related('pool')
    races = await permalink.races.filter(
        status__in=['finished', 'forfeit'], reattempted=False
    ).order_by('-score').prefetch_related('live_race')
    await permalink.fetch_related('live_races')

    return jsonify({
        'tournament': {'id': tournament.id, 'name': tournament.name, 'active': tournament.active},
        'permalink': {
            'id': permalink.id,
            'url': permalink.url,
            'notes': permalink.notes,
            'par_time': permalink.par_time_formatted if permalink.par_time else None,
            'live_race': permalink.live_race,
            'pool_name': permalink.pool.name,
        },
        'races': [
            {
                'id': race.id,
                'status': race.status,
                'elapsed_time': race.elapsed_time_formatted,
                'score_formatted': race.score_formatted,
                'review_status': race.review_status,
            }
            for race in races
        ],
    })
```

### 7.3 Frontend component

File: `alttprbot_api/spa/src/pages/async-tournament/AsyncPermalinkPage.tsx`

- Page head: "PERMALINK" h1, breadcrumb, badges: pool name (gold), par time if set (Space Mono, teal)
- Permalink details panel: URL (external link), notes, par time, live race badge
- Races table: Status | Time | Score | Review
- 403 state: tournament active, not authorized

---

## 8. `/triforcetexts/:pool` — Triforce Text Submission

**Purpose**: Players submit three lines of text (up to 19 chars each, with a specific character allowlist) that appear in-game as Triforce text.

**Auth**: Required (Discord session). Character regex: `^[A-Za-z0-9 ?!,-….~～''↑↓→←あいうえおやゆよかきくけこわをんさしすせそがぎぐたちつてとげございにぬねのじずぜはひふへほぞだぢまみむめもづでどらりるれろばびぶべぼぱぴぷぺぽゃゅょっぁぃぅぇぉアイウエオヤユヨカキクケコワヲンサシスセソガギグタチツテトゲゴザナニヌネノジズゼハヒフヘホゾダマミムメモヅデドラリルレロバビブベボパピプペポャュョッァィゥェォ]{0,19}$`

### 8.1 Existing routes

- `GET /triforcetexts/<pool_name>` — renders submission form (requires auth)
- `POST /triforcetexts/<pool_name>/submit` — processes submission

**Do not remove these** — keep them as fallback. The SPA can call the existing POST endpoint since it accepts `application/x-www-form-urlencoded`. Or add a JSON POST:

### 8.2 New backend JSON endpoint

Add to `triforcetexts.py`:

```python
from quart import jsonify as quart_jsonify  # already imported as jsonify if not present

@triforcetexts_blueprint.route('/triforcetexts/<string:pool_name>/api', methods=['POST'])
@requires_authorization
async def submit_json(pool_name):
    user = await discord.fetch_user()
    payload = await request.get_json(force=True) or {}

    regex = re.compile(
        r"^[A-Za-z0-9 ?!,-….~～''↑↓→←あいうえおやゆよかきくけこわをんさしすせそがぎぐたちつてとげございにぬねのじずぜはひふへほぞだぢまみむめもづでどらりるれろばびぶべぼぱぴぷぺぽゃゅょっぁぃぅぇぉアイウエオヤユヨカキクケコワヲンサシスセソガギグタチツテトゲゴザナニヌネノジズゼハヒフヘホゾダマミムメモヅデドラリルレロバビブベボパピプペポャュョッァィゥェォ]{0,19}$")

    for line_key in ('first_line', 'second_line', 'third_line'):
        val = payload.get(line_key, '')
        if not regex.match(val):
            return jsonify({'error': f'Invalid characters in {line_key}. Max 19 characters from the allowed set.'}), 400

    text = f"{payload.get('first_line', '')}\n{payload.get('second_line', '')}\n{payload.get('third_line', '')}"
    await models.TriforceTexts.create(pool_name=pool_name, text=text, discord_user_id=user.id,
                                      author=user.name)
    return jsonify({'success': True})
```

**Note**: check `from quart import jsonify` is imported in `triforcetexts.py` — add if missing.

### 8.3 Frontend component

File: `alttprbot_api/spa/src/pages/TriforceTextsPage.tsx`

- Page head: "TRIFORCE TEXTS" h1, breadcrumb (Home / Triforce Texts), pool badge (gold)
- Auth prompt if not signed in
- Submission form:
  - Three text inputs: Line 1, Line 2, Line 3 (each max 19 chars, client-side length counter)
  - Real-time validation: show character count, crimson if > 19
  - Submit → POST to `/triforcetexts/:pool/api`
  - Success panel: "Your text has been submitted! It will appear after moderation approval."
  - Error panel with validation message from server
- Sidebar info panel: "What is Triforce Text? — Three lines of up to 19 characters that appear in your copy of the randomized game. Use English or Japanese characters."

---

## 9. `/triforcetexts/:pool/moderation` — Triforce Text Moderation

**Purpose**: Moderators approve or reject submitted triforce texts.

**Auth**: Required. User must be in the moderators list for the pool (stored in `TriforceTextsConfig` with `key_name='moderator'`).

### 9.1 Existing routes

- `GET /triforcetexts/<pool_name>/moderation` — renders moderation queue
- `GET /triforcetexts/<pool_name>/moderation/<text_id>/<action>` — approve/reject action (redirect-based)

**Keep existing routes** but also add JSON endpoints:

```python
@triforcetexts_blueprint.route('/triforcetexts/<string:pool_name>/moderation/api', methods=['GET'])
@requires_authorization
async def moderation_json(pool_name):
    user = await discord.fetch_user()
    config_entries = await models.TriforceTextsConfig.filter(pool_name=pool_name, key_name='moderator')
    moderators = [int(x.value) for x in config_entries]
    if user.id not in moderators:
        return jsonify({'error': 'Access denied.'}), 403

    approved_filter = request.args.get('approved', 'pending')
    filt = {'pool_name': pool_name}
    if approved_filter == 'true':
        filt['approved'] = True
    elif approved_filter == 'false':
        filt['approved'] = False
    elif approved_filter == 'pending':
        filt['approved__isnull'] = True

    texts = await models.TriforceTexts.filter(**filt)
    return jsonify({
        'pool_name': pool_name,
        'filter': approved_filter,
        'texts': [
            {'id': t.id, 'text': t.text, 'author': t.author, 'approved': t.approved}
            for t in texts
        ],
    })


@triforcetexts_blueprint.route('/triforcetexts/<string:pool_name>/moderation/api/<int:text_id>', methods=['POST'])
@requires_authorization
async def moderation_action_json(pool_name, text_id):
    user = await discord.fetch_user()
    config_entries = await models.TriforceTextsConfig.filter(pool_name=pool_name, key_name='moderator')
    moderators = [int(x.value) for x in config_entries]
    if user.id not in moderators:
        return jsonify({'error': 'Access denied.'}), 403

    payload = await request.get_json(force=True) or {}
    action = payload.get('action')  # 'approve' or 'reject'
    if action not in ('approve', 'reject'):
        return jsonify({'error': 'Invalid action.'}), 400

    text = await models.TriforceTexts.get_or_none(id=text_id)
    if text is None:
        return jsonify({'error': 'Text not found.'}), 404

    text.approved = action == 'approve'
    await text.save()
    return jsonify({'success': True, 'approved': text.approved})
```

**Note**: Check if `jsonify` is imported in `triforcetexts.py`; add `from quart import ..., jsonify` if needed.

### 9.2 Frontend component

File: `alttprbot_api/spa/src/pages/TriforceTextsModerationPage.tsx`

- Page head: "TEXT MODERATION" h1, breadcrumb (Home / Triforce Texts / Moderation), pool badge + "MODERATOR" crimson badge
- Filter tabs: Pending | Approved | Rejected
- Cards (one per text): author name, three lines of text rendered clearly, Approve / Reject buttons
  - Approved: green check, Reject button shown
  - Rejected: red X, Approve button shown
  - Pending: both buttons shown
  - Clicking Approve/Reject calls POST to `…/moderation/api/:textId` with `{action}`, updates card in-place (no full reload)
- 403 state: "You are not a moderator for this pool."
- Empty state: "No texts in this category."

---

## 10. `/ranked_choice/:id` — Ranked Choice Ballot

**Purpose**: Authenticated users rank candidates for an election. One submission per user; after submitting, shows existing votes read-only.

**Auth**: Required. May also require guild membership + role if `election.private`.

### 10.1 Existing routes

- `GET /ranked_choice/<election_id>` — renders ballot (or existing votes if already voted)
- `POST /ranked_choice/<election_id>` — submits ballot

The POST uses `application/x-www-form-urlencoded` with keys `candidate_<id>` mapped to rank integers. The SPA can replicate this with a JSON endpoint.

### 10.2 Model reference

```python
# models.RankedChoiceElection: id, name, active, private, guild_id, voter_role_id
# models.RankedChoiceCandidate: id, election FK, name, description (if exists)
# models.RankedChoiceVotes: id, election FK, candidate FK, user_id, rank
```

Check the actual model fields: `grep -A 30 "class RankedChoiceElection" alttprbot/models/models.py`

### 10.3 New backend JSON endpoints

Add to `ranked_choice.py`:

```python
from quart import jsonify  # add to imports if missing

@ranked_choice_blueprint.route('/ranked_choice/<int:election_id>/api', methods=['GET'])
@requires_authorization
async def get_ballot_json(election_id: int):
    user = await discord.fetch_user()
    try:
        election = await models.RankedChoiceElection.get(id=election_id)
    except tortoise.exceptions.DoesNotExist:
        return jsonify({'error': 'Election not found.'}), 404

    if not election.active:
        return jsonify({'error': 'Election is inactive.'}), 404

    if election.private:
        guild = await discordbot.fetch_guild(election.guild_id)
        voter_role = guild.get_role(election.voter_role_id)
        try:
            member = await guild.fetch_member(user.id)
        except Exception:
            return jsonify({'error': 'Unable to find you in the server.'}), 403
        if voter_role not in member.roles:
            return jsonify({'error': 'Not authorized to vote.'}), 403

    await election.fetch_related('candidates')
    existing_votes = await election.votes.filter(user_id=user.id)

    return jsonify({
        'election': {
            'id': election.id,
            'name': election.name,
            'candidates': [
                {'id': c.id, 'name': c.name}
                for c in election.candidates
            ],
        },
        'existing_votes': [
            {'candidate_id': v.candidate_id, 'rank': v.rank}
            for v in existing_votes
        ] if existing_votes else None,
        'already_voted': bool(existing_votes),
    })


@ranked_choice_blueprint.route('/ranked_choice/<int:election_id>/api', methods=['POST'])
@requires_authorization
async def submit_ballot_json(election_id: int):
    user = await discord.fetch_user()
    try:
        election = await models.RankedChoiceElection.get(id=election_id)
    except tortoise.exceptions.DoesNotExist:
        return jsonify({'error': 'Election not found.'}), 404

    if not election.active:
        return jsonify({'error': 'Election is inactive.'}), 404

    await election.fetch_related('candidates')
    existing_votes = await election.votes.filter(user_id=user.id)
    if existing_votes:
        return jsonify({'error': 'Already voted.'}), 403

    payload = await request.get_json(force=True) or {}
    # payload: {"votes": [{"candidate_id": 1, "rank": 1}, ...]}
    votes_data = payload.get('votes', [])

    ranks = [v['rank'] for v in votes_data if v.get('rank')]
    if len(ranks) != len(set(ranks)):
        return jsonify({'error': 'Each rank must be unique.'}), 400

    votes = []
    for vote in votes_data:
        candidate = next((c for c in election.candidates if c.id == vote['candidate_id']), None)
        if not candidate:
            return jsonify({'error': f"Invalid candidate {vote['candidate_id']}"}), 400
        votes.append(models.RankedChoiceVotes(
            election=election, candidate=candidate, user_id=user.id, rank=vote['rank']
        ))

    votes.sort(key=lambda v: v.rank)
    await models.RankedChoiceVotes.bulk_create(votes)
    await rankedchoice.refresh_election_post(election, discordbot)

    return jsonify({'success': True})
```

### 10.3 Frontend component

File: `alttprbot_api/spa/src/pages/RankedChoicePage.tsx`

- Page head: "RANKED CHOICE" h1, breadcrumb (Home / Ranked Choice), election name badge (gold)
- Auth prompt if not signed in
- **Already voted state**: read-only display of their rankings — "Your votes are locked." with teal confirmation badge
- **Ballot state**: drag-and-drop OR simple select-per-candidate form
  - For simplicity: each candidate gets a `<select>` for rank 1…N (must be unique — validate client-side)
  - Submit button → POST to `.../api`
  - On success: transition to "already voted" state showing their choices
- Error states: inactive election, not authorized (wrong guild/role)

---

## 11. `/sglive` — SG Live Dashboard

**Purpose**: Simple dashboard linking to seed generators for each active game category. The generator links (`/sglive/generate/alttpr` etc.) are server-side redirects to external seed URLs — keep them as-is.

**Auth**: None required.

### 11.1 Existing Jinja GET route

`sglive.py`, `sglive_dashboard` — builds a `games` list in Python (hardcoded, not from DB) and passes to template. **Remove this route** when done.

The generate routes (`/sglive/generate/alttpr` etc.) are **not removed** — they are server-side redirects that the SPA links to as external `<a href>` elements.

### 11.2 New backend JSON endpoint

Add to `sglive.py`:

```python
@sglive_blueprint.route('/api', methods=['GET'])
async def sglive_dashboard_json():
    games = [
        {'name': 'OOTR', 'generator_url': '/sglive/generate/ootr'},
        {'name': 'ALTTPR', 'generator_url': '/sglive/generate/alttpr'},
        {'name': 'FFR', 'generator_url': '/sglive/generate/ffr'},
        {'name': 'SMR', 'generator_url': '/sglive/generate/smr'},
        {'name': 'SMZ3', 'generator_url': '/sglive/generate/smz3'},
    ]
    return jsonify({'games': games})
```

Check if `jsonify` is imported in `sglive.py`; add to imports if not.

Also remove the Jinja GET route `sglive_dashboard` (the `/` route registered on the blueprint) — the SPA catch-all can serve `/sglive`.

**Note**: `/sglive/` is in `_RESERVED_PREFIXES` in `api.py`. Change it to `/sglive/generate/` and `/sglive/reports/` so the SPA catch-all can handle `/sglive` and `/sglive/reports/capacity`.

### 11.3 Frontend component

File: `alttprbot_api/spa/src/pages/SGLiveDashboardPage.tsx`

- Page head: "SG LIVE" h1, breadcrumb (Home / SG Live), "SPEEDGAMING" badge (gold)
- Grid of game cards — one per game in the JSON response:
  - Game name (large, Cinzel Decorative)
  - "Generate Seed →" link: `<a href={game.generator_url}>` (server-side redirect to external seed URL — NOT a React Router Link)
  - Add a warning note: "Seed generation may take a moment. You will be redirected to the seed URL."
- Info blurb: "These are the active games for the current SGL season. Click Generate to roll a fresh seed."

Add to router: `{ path: '/sglive', element: <SGLiveDashboardPage /> }`

---

## 12. Implementation Notes

### File conflicts to avoid in parallel agents

The following files will be edited by multiple pages — **assign one agent per file** to avoid conflicts:

| File | Owned by agent |
|---|---|
| `asynctournament.py` | Async tournament pages agent (§3–7) |
| `triforcetexts.py` | Triforce texts agent (§8–9) |
| `ranked_choice.py` | Ranked choice agent (§10) |
| `sglive.py` | SG Live agent (§11) |
| `router.tsx` | **Merge manually** after all agents complete |
| `api.py` `_RESERVED_PREFIXES` | Update after agents complete (see §11.2 for sglive change) |

### Suggested parallel split

- **Agent A**: §3 (Reattempt) + §4 (Queue) + §5 (Review) + §6 (Pools) + §7 (Permalink) — all async tournament
- **Agent B**: §8 (Triforce Submit) + §9 (Triforce Moderation) — same blueprint file
- **Agent C**: §10 (Ranked Choice) + §11 (SG Live) — separate blueprint files, no conflict

### After all agents finish

1. Merge `router.tsx` manually (add all new imports + routes)
2. Update `_RESERVED_PREFIXES` in `api.py` for sglive change
3. Build SPA: `cd alttprbot_api/spa && PATH="$HOME/.nvm/versions/node/v20.20.2/bin:$PATH" npm run build`
4. Restart server and smoke-test each new route
