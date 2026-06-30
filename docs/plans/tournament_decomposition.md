# Tournament Decomposition Plan

> The detailed execution plan for decomposing the live-tournament god-object
> (`alttprbot/tournament/`) into the strict three-tier architecture. This expands the
> "Tournament Decomposition" section of
> [three_tier_migration.md](three_tier_migration.md) into a concrete, PR-by-PR plan.
> Grounded in a five-dimension analysis of the package (base anatomy, subclass catalog,
> discord coupling, data/racetime I/O, registry/config path).

## 0. Progress

- **PR 0 (done, `0832bf36`)** — scaffolding: `SeedResult`, `TournamentDefinition`, and the
  discord/racetime gateway protocol extensions. Pure additive; tested.
- **PR 0.5 (done, `27cc7003`)** — concrete `DiscordGatewayImpl` + `RaceTimeGatewayImpl`,
  registered inward at startup. Both satisfy their `runtime_checkable` protocols.
- **PR 1 (done, `259afaf5`)** — `TournamentPresenter` (gateway-based embeds / audit / commentary /
  player DMs), fully unit-tested with a mock gateway. Not yet wired.
- **All reusable collaborators now exist** (DTOs, gateways, presenter).
- **PR 2 (done, `66758e24`)** — `TournamentOrchestrator` base (pure business; gateways/repos/
  resolver-callbacks injected; no discord/racetime imports) + `TestOrchestrator` + the
  `OrchestratorAdapter` (transitional bridge presenting the legacy dispatch interface) +
  `TOURNAMENT_DATA['test']` wired to it. The **room-creation lifecycle** path is proven
  end-to-end for the debug-only `test` handler. Verified by a 3-agent adversarial OLD-vs-NEW
  parity review; folded in its findings (critical: the adapter now resolves the definition into
  a live `TournamentConfig` so the un-migrated cog's `get_config()` accessors keep working;
  restored room-name + DM-failure logging; unresolved-member → DM skip parity). 362 tests.

- **PR 3 (done)** — the seed-rolling path, with `boots` as the first concrete handler. Added the
  shared `ALTTPRTournamentOrchestrator` (`services/tournament/alttpr.py`) — a behavior-preserving
  port of the legacy `ALTTPRTournamentRace`: `process_race` (the `!tournamentrace` flow),
  `send_room_welcome` (welcome + pinned "Roll Tournament Seed" action), `_seed_code`. `BootsOrchestrator`
  overrides only `roll()` (the `casualboots` preset → `SeedResult`). Collaborator extensions:
  `TournamentResultsRepository.create_or_update_with_permalink`,
  `discord_gateway.send_channel_message(mention_everyone=)`, `racetime_gateway.send_pinned_action(...)`
  + `get_entrant_ids(...)`, presenter `build_race_embeds` / `send_player_seed_dm` (→bool) /
  `send_audit_alert`. `process_race` returns whether a seed was rolled; the adapter sets the handler's
  `seed_rolled` guard only on success and refreshes the room (name/url) before delegating. Registry
  repoints `boots` → `make_adapter(BootsOrchestrator, BOOTS_DEFINITION)`. 18 new tests; 380 passing;
  import-linter still 3-kept. Verified by a 5-lens adversarial OLD-vs-NEW parity workflow (23 findings,
  every one independently re-verified): **1 real divergence found and fixed** — the per-entrant seed-URL
  RaceTime whisper must read the entrant list *post-roll/live* (legacy read `handler.data['entrants']` at
  the loop, after the seconds-long seed gen), so it now reads fresh via `racetime_gateway.get_entrant_ids`
  instead of the pre-roll room snapshot. All other findings refuted as parity/known-safe.

- **PR 4 (done)** — the trivial/low ALTTPR tail, batched (the PR-3 pattern is now mechanical):
  `services/tournament/{smwde,nologic,alttprhmg,alttprde,alttprmini}.py`, each a small orchestrator
  overriding only `roll()` + a `<EVENT>_DEFINITION` lifting the hardcoded IDs out of the legacy
  `configuration()`; registry repointed to `make_adapter(...)`. `smwde` is pure-config (SM hacks, no
  seed roll) so it extends the **base** `TournamentOrchestrator` (no-op `process_race`, no welcome) —
  matching the legacy `SMWDETournament` on the base `TournamentRace`. `nologic`/`alttprhmg` are
  fixed-preset rolls; `alttprde`/`alttprmini` share a new `ALTTPRTournamentOrchestrator._roll_from_title_map`
  helper (split title on the last `:`, strip, map lookup; unknown title → "Invalid mode chosen" race
  message + re-raise) differing only in their title→preset map. 14 new tests (title-map success +
  KeyError path, fixed-preset kwargs, every definition's IDs); 394 passing; import-linter 3-kept.
  Verified by a per-handler adversarial parity workflow (5 reviewers reading legacy-vs-new digit/entry
  by entry): **0 findings — clean parity across all five.**

- **PR 5 (done)** — the ALTTPR **league** handlers (`invleague` + `alttprleague`). The legacy
  `ALTTPRLeague`/`ALTTPROpenLeague` differed only in `event_slug`, so both collapse into one
  `ALTTPRLeagueOrchestrator` (`services/tournament/alttprleague.py`) parameterised by
  `INVITATIONAL_LEAGUE_DEFINITION` / `OPEN_LEAGUE_DEFINITION`. League-specific overrides on the shared
  ALTTPR seed-roll lifecycle: `update_data` also fetches the external `alttprleague.com/api/episode`
  "mode" (preset + spoiler/co-op flags); `room_creation_kwargs` derives the dynamic goal /
  `team_race` / `require_even_teams`; `roll` rolls the league preset or a spoiler game (scheduling the
  spoiler race via the gateway); `send_room_welcome` is a no-op (league suppressed it). The legacy
  in-`roll` `create_embeds` (built twice, only the second used) is dropped — the presenter builds the
  embeds once in `process_race`. 9 new tests (mode fetch + error path, room kwargs solo/co-op/spoiler,
  preset vs spoiler roll, no-op welcome, both definitions); 403 passing; import-linter 3-kept. Two
  adversarial parity reviewers (overrides + ID/wiring): **clean — no divergences, IDs match digit-for-digit.**
- **Registry unification (done, post-PR5)** — the dual-source drift is eliminated.
  `_HARDCODED_TOURNAMENT_DATA` (the fallback used when `TOURNAMENT_CONFIG_ENABLED` is false — the
  **production default**) is now *derived* from `AVAILABLE_TOURNAMENT_HANDLERS`:
  `{slug: AVAILABLE_TOURNAMENT_HANDLERS[slug] for slug in _HARDCODED_ACTIVE_SLUGS}`. The fallback lists
  declare only *which slugs* are active per profile; the *handler class* always comes from the catalog,
  so the hardcoded path, the `config/tournaments.yaml` path, and the catalog can never disagree. The
  production active set is unchanged (`alttpr`, `alttprdaily`, `smz3`, `invleague`, `alttprleague`) — the
  one behavioral effect is that `invleague`/`alttprleague` now dispatch to the migrated (parity-reviewed)
  orchestrator under the default path too, matching the config path. A no-drift regression test pins the
  invariant (`tests/unit/services/test_tournament_registry.py`). **Because production runs the hardcoded
  path, do a DEBUG/staging smoke test of the league rooms before the next deploy** — the new code is
  static-parity-clean but not yet live-validated. Migrating a future handler in the catalog now
  propagates to both paths automatically (no second registry edit).

- **PR 6 (done)** — `smrl_playoff` (the Super Metroid Random League playoffs — `smrl`). The heaviest
  handler so far. `SMRLPlayoffsOrchestrator` (`services/tournament/smrl.py`) extends the **base**
  orchestrator (no ALTTPR embeds) and overrides: `process_race` (SM seeds via `SuperMetroidVaria` /
  `smdash`, whisper the seed URL + set race-info, persist the permalink), `send_room_welcome` (a single
  pinned welcome message carrying the action), `before_room_creation` (gate room creation on submitted
  settings), and `process_submission_form` (map game# → randomizer/preset, persist, confirm). New shared
  infrastructure: base `before_room_creation` gate + adapter honoring it; base `send_race_submission_form`
  (reminders via presenter + `submitted` upsert) + base `process_submission_form` no-op; presenter
  `send_player_reminders` + `send_submission_confirmation` (+ `_submission_dm_failed`); adapter
  `process_submission_form` / `send_race_submission_form` / `versus` delegation; `TournamentDefinition.submission_form`
  widened to `Any` so it can carry the SMRL form schema (`SMRL_SUBMISSION_FORM`). Registry repoints `smrl`
  (seasonal — stays dormant in the production hardcoded set). 24 new tests; 431 passing; import-linter
  3-kept. Verified by a 5-surface adversarial parity workflow (13 findings, **0 confirmed real**); the one
  "uncertain" was a doc nit — the submission gate cleanly drops a *latent legacy crash* (legacy returned
  `None` from `create_race_room`, which the un-null-checked base dereferenced → `AttributeError` + a
  spurious audit error). Docstrings corrected to describe this as an intentional cleanup, not a mirror.

- **PR 7 (done)** — the SG dailies (`alttprdaily` + `smz3`), the first **active production** handlers to
  migrate. Open casual races: `SGDailyOrchestrator` (`services/tournament/dailies.py`) extends the **base**
  orchestrator and overrides `room_creation_kwargs` (`invitational=False`, `team_race` from a "co-op" title
  match), `update_data` (fetch episode/game/team, resolve **no** players — open race), `race_info` / `seed_time`,
  and `send_player_room_info` → a channel **announcement** (`alttprdaily` also posts the SG webhook) instead of
  player DMs. Two thin subclasses set the per-event presentation (series label, seed-time inclusion, role-mention
  prefix, webhook). New collaborators: presenter `send_race_announcement` (discord timestamps + role mentions +
  optional webhook), gateway `send_channel_message(mention_roles=)` + `send_webhook(username=)`. 12 new tests; 443
  passing; import-linter 3-kept. Verified by a 4-surface adversarial parity workflow (15 findings, **0 behavior
  divergences** — every announce/race-info string confirmed byte-for-byte; the one "confirmed" was a stale registry
  comment, fixed). **Production runs the hardcoded path, so the dailies go live on the next deploy — smoke-test in
  DEBUG first.**

- **PR 8 (done)** — `alttpr_quals` (the ALTTPR main-tournament live qualifier, slug `alttpr`): the last and
  most entangled active handler. `ALTTPRQualifierOrchestrator` (`services/tournament/alttpr_quals.py`) extends the
  base orchestrator with the full live-race ↔ AsyncTournament flow: `before_update_data` (live-race gate, runs
  *before* any I/O), `process_race` (guard ladder, mod/admin authz, room-lock, `triforce_text` seed, permalink
  persistence, eligible-entrant writes), `on_race_start` (promote present entrants, prune no-shows, announce), plus
  the open-race `update_data`/`race_info`/announce. New repo methods on `AsyncTournamentLiveRaceRepository`
  (`get_by_episode_id[_with_relations]`, `set_permalink_and_slug`, `process_race_start`), `AsyncTournamentRepository`
  (`create_live_permalink`, `count_completed_pool_races`, `user_has_active_race`, `create_pending_live_entry`), and
  `UserRepository` (`get_or_create_by_rtgg_id`, `set_twitch_name`); gateway `get_entrants`/`get_started_at`; presenter
  `seed_label`; an adapter-supplied async-authz callback (wraps `checks.is_async_tournament_user`) + a new
  `before_update_data` pre-I/O gate hook. 18 unit + 4 repo round-trip tests; 462 passing; import-linter 3-kept.
  Verified by a 5-surface adversarial parity workflow (16 findings, **1 confirmed (low)** — the live-race gate ran
  *after* `update_data`; fixed by the pre-I/O `before_update_data` hook so a no-live-race episode short-circuits
  before any SpeedGaming/RaceTime call, matching legacy). **Active production handler — smoke-test in DEBUG before deploy.**

**★ MILESTONE — every active tournament handler is now a decomposed orchestrator.** All slugs in the production
registry (`alttpr`, `alttprdaily`, `smz3`, `invleague`, `alttprleague`) and every seasonal slug dispatch through
`services/tournament/` orchestrators + the presenter + gateways; no legacy god-object class is active.

- **PR 9 (done) — final cleanup.** Deleted the 18 now-unused legacy handler subclass files under
  `alttprbot/tournament/` (`boots`/`smwde`/`smrl_playoff`/`alttprleague`/`nologic`/`alttprhmg`/`alttprde`/`alttprmini`/
  `alttpr_quals`/`test` + the `dailies/` package + the long-dead `alttpres`/`alttprfr`/`smz3coop`/`smbingo`/`smrl`/
  `alttprsglive`/`alttprcd`), dropped the unused legacy-handler imports from `tournaments.py`, and routed
  `create_tournament_race_room`'s lone `racetime_bots` lookup through the racetime gateway so the racetime-bot import
  is gone. The `alttprbot/tournament/` package is now just the dispatch infra: `orchestrator_adapter.py` (the untiered
  bridge), `registry_loader.py` (the YAML config path), and the `core.py` (`TournamentConfig` +
  `UnableToLookupUserException`) / `alttpr.py` shims the discord cog still imports (type hints + the pre-existing-broken
  cc2023 `roll_seed`/`generate_deck` commands — out of scope). 462 passing; import-linter 3-kept.

## ★ Decomposition complete

Every tournament handler is decomposed: the business orchestrators live in `alttprbot/services/tournament/`
(actively under the import-linter layering + bot-singleton contracts), Discord rendering in
`alttprbot/presentation/discord/tournament/presenter.py`, all RaceTime/Discord I/O behind the `_notify` gateways, and
all ORM behind repositories. The `OrchestratorAdapter` is the one remaining transitional piece — an intentionally
**untiered** bridge (in `alttprbot/tournament/`) that still touches `discordbot` for player/authz resolution and holds
the live RaceTime handler, presenting the legacy dispatch interface to the un-migrated discord cog + racetime handler.

**Follow-ups (beyond the handler decomposition):**
- Retire the `OrchestratorAdapter` by rewiring the discord cog (`cogs/tournament.py`) and racetime handler
  (`handlers/core.py`) to drive `(orchestrator, presenter)` directly — then `alttprbot/tournament/` can be deleted
  entirely and the package relocated semantics finished. This is a dispatch-surface refactor, not a handler change.
- Each migrated handler is static-parity-clean but **not yet live-validated**; smoke-test the active ones
  (`alttpr`, `alttprdaily`, `smz3`, `invleague`, `alttprleague`) in DEBUG/staging before the next production deploy
  (production runs the hardcoded path, so they go live on deploy).
- Phase 10: flip the import-linter contracts to blocking + `SAHASRAHBOT_HOOKS_ENFORCE=1` once the guild-config
  monkey-patch + legacy `database/config.py` also land.

**RECOMMENDATION:** validate `boots` (full seed-roll) and one title-map event (`alttprde`) in DEBUG —
confirm the room opens, the seed rolls from the title, embeds/DMs/audit/permalink fire, and a bad title
posts "Invalid mode chosen" — before tackling the moderate handlers. The whole ALTTPR tail now shares
the exact same exercised collaborators, so a single live pass de-risks it.

## 1. Why this is the last big piece

Every import-linter contract is currently **KEPT** — but only because `alttprbot/tournament/`
is **untiered** (it sits outside the `services`/`presentation` path prefixes the contracts
govern). It is a genuine god-object: `TournamentRace` (core.py, 462 lines) and ~20 subclasses
mix **five concerns per method** — business orchestration, Discord rendering, Discord-ID
resolution, RaceTime I/O, and direct ORM. The moment we relocate it into
`alttprbot/services/tournament/` (its architectural home), Contracts 1 & 2 would break — so the
relocation *requires* the decomposition. This plan extracts the presenter/gateway/repository
collaborators first, then relocates the now-pure orchestrator.

**Scale:** ~2723 lines / 20 files. ~75 `discordbot` singleton calls. ~123 hardcoded Discord
snowflake IDs across 23 `configuration()` overrides. 24 ORM patterns. 11 RaceTime gateway
patterns. 11 active handlers (5 production + 1 debug + 5 dailies); 9 dead/commented.

**Already done (leverage these):** Phase 7a landed `TournamentResultsRepository` +
`TournamentGamesRepository` and rewired the base ORM (core.py:156, 243, 460). The seed-embed
extraction landed `presentation/discord/util/seed_embeds.py` (`seed_embed` /
`seed_tournament_embed`) and `services/seedgen/seedclasses.py`. `UserService`/`UserRepository`
already expose `get_by_discord_id` / `get_by_rtgg_id`. The `AsyncTournament*` repos/services
(built during the cog burn-down) back the qualifier handler. So the data tier is largely in
place; this work is mostly the **discord/racetime/embed** extraction + relocation.

## 2. Current architecture

```
SpeedGaming schedule ─┐
                      ▼
  discord cog tournament.py ── create_race_room(slug, episode) ─┐
                                                                 ▼
  alttprbot/tournaments.py  TOURNAMENT_DATA[slug].construct_race_room(episodeid)
        │  (maps event-slug → TournamentRace subclass; imports racetime bot ⚠)
        ▼
  TournamentRace subclass (god-object)
        │  configuration() → hardcoded discordbot.get_guild/get_channel/get_role(<id>)
        │  update_data()   → speedgaming + TournamentGamesRepository + racetime bot + player lookup
        │  create_race_room() → racetime startrace
        │  roll()          → seedgen + builds discord.Embed
        │  process_tournament_race() → racetime msgs + ORM writes + embeds + DMs
        ▲
  racetime handler core.py:297  self.tournament.process_tournament_race(args, message)
                                 + on_race_start / on_room_creation / on_room_resume
```

**Dispatch sites (3):** the discord cog background task, the racetime handler room-resume/attach,
and `api/blueprints/tournament.py` (read-only `get_config`). All read the module-level
`TOURNAMENT_DATA` dict.

**The architecture smell:** `alttprbot/tournaments.py:10` does
`from alttprbot.presentation.racetime import bot as racetimebot`, and every subclass imports
`from alttprbot.presentation.discord.bot import discordbot`. These are the singleton couplings
that the gateway pattern replaces.

## 3. Target architecture

```
Presentation                          Service                         Repository
─────────────                         ────────                        ──────────
discord cog / racetime handler        services/tournament/core.py     tournament_results_repository
  → resolve definition (config)         TournamentOrchestrator          tournament_games_repository
  → build orchestrator + presenter      (business only)                 user_repository
  → drive lifecycle                       roll() → SeedResult           async_tournament_* repos
                                          update_data(), can_gatekeep()
presentation/discord/tournament/          lifecycle hooks
  presenter.py  TournamentPresenter     services/tournament/<event>.py
  → SeedResult → discord.Embed            per-event orchestrator
  → resolve channel/role ids              (overrides roll()/hooks only)
  → send DMs / audit / commentary
                                        gateways (protocols in services,
                                        impls registered inward at startup):
                                          discord_gateway  (extend _notify)
                                          racetime_gateway (new)
```

### 3.1 Collaborators and their APIs

**`SeedResult` (neutral DTO, `services/seedgen` or `services/tournament/types.py`)** — the
presentation-neutral hand-off so the orchestrator never builds an embed:
```python
@dataclass
class SeedResult:
    seed: object            # the *Seed object (services/seedgen/seedclasses) — carries url/code/hash
    preset: str | None
    settings_summary: str | None
    spoiler_url: str | None = None
    # the presenter calls seed_embed(seed, emojis=...) — embeds never built in the service tier
```

**`TournamentOrchestrator` (`services/tournament/core.py`, base; business only)**
- Constructed with injected collaborators: `results_repo`, `games_repo`, `user_repo`,
  `seedgen` service, `discord_gateway`, `racetime_gateway`, `speedgaming`, and a
  `TournamentDefinition`. **No `discordbot`/`racetime` singleton imports, no direct ORM, no
  `discord.Embed`.**
- Keeps: `construct` / `construct_race_room` / `construct_with_episode_data` (factory),
  `update_data`, `can_gatekeep`, `process_tournament_race`, and the pure-data properties
  (`player_*`, `race_info`, `versus`, `race_start_time`, `seed_code`, timing).
- Business template hooks (overridden per event): `roll() -> SeedResult`,
  `seed_code`/`submission_form` (data), and the lifecycle hooks
  `on_room_creation`/`on_room_resume`/`on_race_start`/`on_race_pending`. The hook **bodies** move
  from subclasses into per-event orchestrators; the hooks that today do presentation
  (`create_embeds`, `send_*`) are **removed** from the orchestrator and called on the presenter.
- Deletes (replaced by injected `TournamentDefinition`): `configuration()`, the `guild` /
  `audit_channel` / `commentary_channel` properties, and the discord-object fields on
  `TournamentConfig`.

**`TournamentPresenter` (`presentation/discord/tournament/presenter.py`)**
- `create_embeds(seed_result, race_info, versus, broadcast_channels, emojis)` — builds the seed
  embeds via `seed_embed`/`seed_tournament_embed` (already extracted).
- `send_player_room_info(player_ids, rtgg_url)`, `send_player_seed_dm(player_id, seed_result)`,
  `send_audit_message(definition, msg, embed)`, `send_commentary_message(definition, embed)`,
  `send_race_submission_form(...)`.
- Owns id→object resolution for sends (via the discord gateway). Receives `TournamentDefinition`
  (IDs) + the orchestrator's neutral results; never reaches into business state.

**`discord_gateway` (extend `services/_notify/discord_gateway.py`)** — protocol methods the
tournament code needs beyond the existing notify surface:
`resolve_guild(guild_id)`, `resolve_channel(channel_id)`, `resolve_role(guild_id, role_id)` /
`resolve_roles(...)`, `get_emojis()`, `send_dm(user_id, embed)`,
`send_channel_message(channel_id, content=, embed=)`, `send_webhook(url, embed)`. Concrete impl
registered inward by `presentation/discord/bot.py` at `on_ready()`.

**`racetime_gateway` (new, `services/_notify/racetime_gateway.py` + protocol)** — the 11
patterns found: `startrace(category, **opts)`, `send_message`, `set_bot_raceinfo`,
`set_invitational`, `invite_user`, `accept_request`, `add_monitor`, `edit`,
`schedule_spoiler_race`, `get_team(slug)`, `http_uri(url)`. Registered inward by
`presentation/racetime/bot.py`.

**`TournamentDefinition` (`services/tournament/definition.py`; loaded by `registry_loader`)** —
replaces the hardcoded IDs in `configuration()`. Fields surfaced by the analysis:
`event_slug`, `racetime_category`, `racetime_goal`, `coop`, `guild_id`, `audit_channel_id`,
`commentary_channel_id`, `mod_channel_id`, `scheduling_needs_channel_id`, `announce_channel_id`,
`helper_role_ids`, `announce_role_id`, `admin_user_ids`, `webhook_urls`, `submission_form`,
`schedule_type`, `streaming_required`.

## 4. Concern → collaborator map (base `core.py`)

| `core.py` member | Current concern(s) | Target |
|---|---|---|
| `TournamentConfig` (dataclass) | holds discord objects + config | split: `TournamentDefinition` (IDs/config) + runtime objects resolved by gateway |
| `TournamentPlayer` | discord member lookup | value object; `make_tournament_player` → repo/gateway factory |
| `construct` / `construct_race_room` / `construct_with_episode_data` | orchestration + discord wait + racetime + ORM | `TournamentOrchestrator` factory; `wait_until_ready` moves to the presentation entry point |
| `configuration()` | hardcoded discord IDs | **delete** → inject `TournamentDefinition` from config |
| `create_race_room()` | racetime `startrace` | `racetime_gateway.startrace(...)` |
| `update_data()` | speedgaming + ORM + racetime + player lookup | orchestrator method w/ injected `speedgaming`, repos, gateway |
| `make_tournament_player()` | guild member resolution | repository/gateway factory (`guild` via `discord_gateway.resolve_guild`) |
| `can_gatekeep()` | racetime + role check | orchestrator (injects gateway + `helper_role_ids` from definition) |
| `send_player_room_info` / `send_*_message` / `send_player_message` | builds embeds + DMs | **presenter** methods |
| `create_embeds()` | `discord.Embed` from seed | **presenter** (`seed_embed`/`seed_tournament_embed`) |
| `process_submission_form()` | form parse (presentation) + ORM (business) | split: presenter parses, orchestrator persists via repo |
| `guild` / `audit_channel` / `commentary_channel` properties | discord-object resolution | **delete** → definition IDs + gateway resolve |
| `player_*` / `race_info` / `versus` / timing properties | pure data | **stay** in orchestrator |
| lifecycle hooks `on_room_*` / `on_race_*` | mixed | **stay as orchestrator hooks**; presentation bodies move to presenter calls |

## 5. Subclass catalog & migration order

**Active (must migrate, in order of risk):**

| Handler | Slug | Lines | Overrides | Complexity | Notes |
|---|---|---|---|---|---|
| `test.TestTournament` | `test` (debug) | 31 | configuration, roll | trivial | **first PR** — debug-only, safe |
| `boots.ALTTPRCASBootsTournamentRace` | `boots` | 19 | configuration, roll | trivial | fixed preset; good early PR |
| `alttprcd.ALTTPRCDTournament` | (dead) | 26 | configuration, roll | trivial | fixed preset |
| `alttprde.ALTTPRDETournament` | `alttprde` | 60 | configuration, roll(title-parse) | low | title→preset map |
| `alttprmini.ALTTPRMiniTournament` | `alttprmini` | 44 | configuration, roll | low | shares DE title-map logic |
| `alttprhmg.ALTTPRHMGTournament` | `alttprhmg` | 28 | configuration, roll | low | |
| `smwde.SMWDETournament` | `smwde` | 20 | configuration | trivial | pure config |
| `nologic.ALTTPRNoLogicRace` | `nologic` | 21 | configuration, roll | low | |
| `alttprleague.ALTTPRLeague` / `ALTTPROpenLeague` | `invleague`/`alttprleague` | 212 | configuration, roll, external API | moderate | injects `alttprleague.com/api/episode` |
| `smrl_playoff.SMRLPlayoffs` | `smrl` | 212 | configuration, roll, process, submission | moderate | submission form + permalink writes |
| `dailies.AlttprSGDailyRace` / `SMZ3DailyRace` | `alttprdaily`/`smz3` | — | configuration, roll | low | daily cron path (separate entry) |
| **`alttpr_quals.ALTTPRQualifierRace`** | **`alttpr`** | **344** | configuration, roll, process, **AsyncTournament integration** | **heavy** | **the only active non-daily handler; entangled with the AsyncTournament* system. Migrate LAST among active, with its own PR + adversarial review.** |

**Dead/commented (skip or delete):** `alttpr.ALTTPRTournamentRace` (internal base used by
`alttpres`/`alttprfr`), `alttpres`, `alttprfr`, `smz3coop`, `smbingo`, `smrl.SMRandoLeague`,
`alttprsglive.ALTTPRSGLive`, `alttprcd`, plus any `ALTTPR2024Race`-style internal bases. Confirm
against the live `config/tournaments.yaml` before deleting; migrate only if reactivated.

**Recommended order:** `test` → `boots`/`smwde` (trivial) → `alttprde`/`alttprmini`/`alttprhmg`/
`nologic` (low) → `alttprleague`/`smrl_playoff` (moderate) → dailies → **`alttpr_quals` last**.

## 6. Repository additions

Existing `TournamentResultsRepository` / `TournamentGamesRepository` cover most ORM; the analysis
found these **new methods** needed (all behind a field allowlist — no mass-assignment):
- `TournamentResultsRepository`: `create_or_update_with_permalink(srl_id, defaults, permalink)`,
  `upsert_with_bingosync(srl_id, defaults, room, password)`,
  `upsert_with_spoiler_and_permalink(srl_id, defaults, spoiler, permalink)`.
- `TournamentGamesRepository`: `create_or_update_with_fields(episode_id, **allowed_fields)`.
- `UserRepository`: `get_by_discord_id` / `get_by_rtgg_id` **already exist**; the qualifier also
  uses the `AsyncTournament*` repos (already built) — map `alttpr_quals` ORM there.

## 7. Registry / config / dispatch changes

- **`registry_loader.py`** (clean, reusable): extend `EventConfig` to carry optional
  `TournamentDefinition` metadata (guild_id, channel_ids, role_ids); `build_active_registry()`
  passes it through to the orchestrator factory. The `config/tournaments.yaml` event blocks gain
  an optional `config:` key with the per-event IDs.
- **`alttprbot/tournaments.py`**: `AVAILABLE_TOURNAMENT_HANDLERS` stays as the capability
  catalog/schema source. After relocation, change imports `from alttprbot.tournament import ...`
  → `from alttprbot.services.tournament import ...` and **remove line 10**
  (`from alttprbot.presentation.racetime import bot`) — that import is the AdHoc coupling the
  gateway replaces. `TOURNAMENT_DATA[slug]` resolves to an orchestrator factory, not a class.
- **Dispatch adapter (coexistence key):** during migration, some slugs map to old
  `TournamentRace` subclasses and some to new orchestrators. Introduce a thin adapter so the
  racetime handler (`core.py:297`) and discord cog can drive **either** an old god-object
  **or** a `(orchestrator, presenter)` pair through the same lifecycle calls. This is what lets
  us migrate one handler per PR without a flag-day.
- **Gateway DI registration:** `presentation/discord/bot.py` registers the concrete
  `discord_gateway` in `on_ready()` (after the bot is ready), and `presentation/racetime/bot.py`
  registers `racetime_gateway` at startup — mirroring the existing `_notify` gateway wiring in
  `sahasrahbot.py`. Services enqueue/resolve through the abstraction only.
- **Rollback safety:** keep the `TOURNAMENT_CONFIG_ENABLED` flag + hardcoded fallback until every
  active handler is migrated and validated in production.

## 8. PR-by-PR sequence

- **PR 0 — Scaffolding (no behavior change).** Create `alttprbot/services/tournament/` package;
  add `SeedResult` + `TournamentDefinition`; add the `racetime_gateway` protocol + concrete impl
  (registered by the racetime bot); extend `discord_gateway` with the resolve/send/webhook
  methods; add an empty `presentation/discord/tournament/presenter.py`. Add the new repository
  methods (§6) with unit tests. Nothing wired yet — old path unchanged.
- **PR 1 — Base orchestrator + presenter, proven with `test`.** Port `core.py` →
  `services/tournament/core.py` as `TournamentOrchestrator` (business only, gateways injected);
  move all presentation methods to `TournamentPresenter`; introduce the dispatch adapter. Migrate
  the **`test`** handler as the first concrete orchestrator. Old subclasses keep running on the
  old base. Verify in DEBUG: room creation, embeds, DMs, audit all identical.
- **PR 2..N — One handler per PR**, in the §5 order. Each: create
  `services/tournament/<event>.py` orchestrator (override `roll()`/hooks only), add its
  `TournamentDefinition` config block (IDs out of `configuration()`), repoint `TOURNAMENT_DATA`,
  delete the old subclass. Trivial handlers can batch 2–3 per PR; `alttprleague`/`smrl_playoff`
  solo; **`alttpr_quals` solo with an adversarial review** (its AsyncTournament entanglement is
  the highest-risk surface).
- **Final PR — Relocate & enforce.** Delete `alttprbot/tournament/`; remove the racetime-bot
  import from `tournaments.py`; confirm import-linter still 3-kept with the code now under
  `services/tournament/` (Contract 4 "tournament business layer must not import the bot
  singletons" now actively guards it). This unblocks the Phase 10 flip to blocking contracts.

## 9. Risks

- **No test coverage on live tournaments.** These drive real races; a broken embed/DM/room is
  user-visible. Mitigate: migrate trivial+debug handlers first to prove the pattern; per-PR DEBUG
  end-to-end exercise; adversarial behavior-preservation review on `alttpr_quals` (and any handler
  touching ORM writes), comparing against the deleted original like the seed-embed work.
- **`alttpr_quals` ↔ AsyncTournament entanglement.** The only active non-daily handler bridges the
  live-tournament and async-tournament systems. It is both the most important and the riskiest;
  do it last, solo, reviewed.
- **Hardcoded-ID extraction (123 IDs).** Transcribing IDs from `configuration()` into config is
  error-prone; a wrong channel/role ID silently misroutes. Mitigate: mechanical extraction script
  + a diff asserting each migrated handler resolves the same IDs as before.
- **Coexistence / dispatch adapter.** Old and new handlers must both work mid-migration; the
  adapter is load-bearing. Keep the hardcoded fallback + flag until done.
- **Gateway DI ordering.** Services may construct before presentation registers a gateway at boot;
  register in `on_ready()` and have gateways enqueue/resolve lazily (the `_notify` queue pattern).

## 10. Verification (per PR)

1. `poetry run lint-imports` — still 3 kept (and after the final PR, the relocated code stays
   clean under the layering + bot-singleton contracts).
2. `poetry run pytest` — orchestrator unit tests (mock gateways/repos; assert `roll()` returns the
   right `SeedResult`, validation raises) + repository round-trips for the new methods.
3. Import every migrated module directly (handlers aren't loaded by `import sahasrahbot`).
4. DEBUG end-to-end: construct the room for the migrated handler, confirm identical embed/DM/audit
   output vs. the pre-migration behavior.
5. For ORM-writing/active handlers: adversarial review diffing the new orchestrator+presenter
   against the deleted subclass.
