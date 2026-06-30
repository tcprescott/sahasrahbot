# Architecture: Strict Three-Tier Layering

> Status: in progress. SahasrahBot is migrating to a strict three-tier
> architecture inside a single `alttprbot/` package. Execution plan:
> [Three-Tier Migration](plans/three_tier_migration.md). Reference model:
> the sibling SGLMan project.

## The tiers

```
Presentation   alttprbot/presentation/{discord,audit,racetime,api}/
                        │  calls services, renders results, catches their errors
                        ▼
Service        alttprbot/services/        business rules, validation, authorization,
                        │                  orchestration, audit logging, notification enqueue
                        ▼
Repository     alttprbot/repositories/    pure Tortoise CRUD/queries; returns models
                        ▼
Models         alttprbot/models/          Tortoise ORM (the database schema)
```

Imports may only point **downward**. A file's tier is its directory.

## Layer responsibilities

### Presentation — `alttprbot/presentation/`
The four surfaces: `discord/` (main bot), `audit/` (audit bot), `racetime/`
(RaceTime.gg bot), `api/` (Quart web API).

- **Does:** parse input, call a service, render the result, catch service errors
  and present them idiomatically per surface (ephemeral Discord reply / error
  embed, RaceTime chat message, Quart JSON + status code), build Discord embeds.
- **Does not:** contain business logic, import `alttprbot.repositories`, or import
  `alttprbot.models`. Data access goes through a service.

### Service — `alttprbot/services/`
One module per domain (`<name>_service.py`), or a subpackage for larger domains
(`services/seedgen/`, `services/tournament/`).

- **Does:** enforce rules and validation, coordinate repositories, write audit
  logs (`AuditService`), enqueue notifications (`_notify`). Instantiated fresh per
  call; injects repositories in `__init__`; otherwise stateless.
- **Raises:** `ValueError` for user-input errors, `PermissionError` for
  authorization failures, `SahasrahBotException` subclasses for domain errors.
- **Does not:** import `discord`, `racetime_bot`, `quart`, or
  `alttprbot.presentation`. To reach a presentation surface, enqueue a coroutine
  on a `_notify` gateway (registered inward by the presentation layer at startup).

### Repository — `alttprbot/repositories/`
One module per domain (`<name>_repository.py`).

- **Does:** static async methods doing Tortoise CRUD/queries; owns
  `prefetch_related`/`.values()`; returns model instances.
- **Does not:** contain business logic, audit, notifications, or any UI import.

### Models — `alttprbot/models/`
Tortoise ORM models. Unchanged by the migration so the Aerich/Tortoise config and
the MySQL schema stay stable.

## Error contract per surface

Services raise; each surface catches centrally and renders:

| Surface | Renders |
|---|---|
| `presentation/discord`, `presentation/audit` | ephemeral reply / error embed (via the `errors` cog) |
| `presentation/racetime` | `await self.send_message(str(e))` to race chat |
| `presentation/api` | `jsonify({'error': str(e)})` with 400/422 (`ValueError`), 403 (`PermissionError`) |

## Notifications

Services never touch the live Discord/RaceTime bot singletons. They enqueue
fire-and-forget work:

```python
from alttprbot.services._notify import discord_gateway, queue
queue.enqueue(discord_gateway.get().send_dm(user_id, embed=payload))
```

The concrete gateway implementations are registered by the presentation layer at
startup (`discord_gateway.register(...)` / `racetime_gateway.register(...)`). Items
enqueued before the worker starts simply wait and drain once it comes up.

## Audit logging

Use `AuditService` with a namespaced `verb.object` action constant from
`AuditActions` (add one when introducing a new action). It is backed by the
existing audit tables — no new generic audit table.

## Adding a feature

1. Add/adjust the model in `alttprbot/models/` (+ `aerich migrate && aerich upgrade` if schema changes).
2. Add/extend the repository in `alttprbot/repositories/`; export it from `__init__.py`.
3. Add/extend the service in `alttprbot/services/`; export it from `__init__.py`.
4. Wire the presentation surface to call the service and render the result/errors.
5. Add a service test (mock the repository).

## Enforcement

Two complementary layers:

- **import-linter** (`pyproject.toml` `[tool.importlinter]`) — runs in CI
  (`.github/workflows/lint.yml`) and pre-commit (`.pre-commit-config.yaml`).
  `poetry run lint-imports`. **Blocking** as of the final migration phase (the CI
  `continue-on-error` was removed): the three contracts are green, so any new
  boundary violation fails the build.
- **Claude Code hooks** (`.claude/scripts/`, wired by `.claude/settings.local.json`) —
  give edit-time feedback during agent sessions: `enforce_architecture.py`
  (PreToolUse), `enforce_no_orm_writes.py` + `check_layer_exports.py` (PostToolUse).
  **Blocking** via `SAHASRAHBOT_HOOKS_ENFORCE=1` set in `.claude/settings.json`.
