# SahasrahBot — Discord Multiworld Deprecation Audit

> Last updated: 2026-02-12
> Scope: `alttprbot_discord/cogs/smmulti.py`, `alttprbot_discord/cogs/doorsmw.py`, `alttprbot_discord/cogs/bontamw.py` (disabled), `alttprbot_discord/bot.py`, `alttprbot/models/models.py` (`Multiworld`, `MultiworldEntrant`, `SMZ3Multiworld`), and adjacent shared-generator callers in RaceTime/tournament flows.

Execution sequencing for this deprecation is tracked in [Discord Multiworld Deprecation & Removal Plan](../plans/discord_multiworld_deprecation_removal_plan.md).

## 1. Component Boundary

This audit covers Discord-hosted multiworld features that are planned for deprecation/removal, plus adjacent dependencies that would be affected by shared code paths.

In-scope runtime surfaces:

- Slash-command interactive SM/SMZ3 multiworld flow in `smmulti`.
- Slash-command Door Randomizer multiworld host-control flow in `doorsmw`.
- Disabled legacy prefix-command Bonta multiworld flow in `bontamw`.
- Cog loading and command registration in `alttprbot_discord/bot.py`.
- Multiworld-related persistence models in `alttprbot/models/models.py`.
- Shared generator dependency `alttprbot/alttprgen/smz3multi.py` and active non-Discord callers in RaceTime and tournament modules.

Out of scope:

- A full RaceTime or tournament deprecation plan.
- Non-multiworld generation features.

## 2. Verified Intent (Owner-Confirmed)

The following policy choices were confirmed directly and are not inferred from code:

- Scope includes Discord multiworld components plus adjacent dependency mapping.
- Deprecation timing is soft deprecate now, remove in the next release.
- Data policy is to drop multiworld tables without archival.
- User-facing behavior after command retirement should be a deprecation message plus a migration pointer.
- Migration target is no functional replacement; feature is retired.
- Primary rationale to document: low/declining usage and simplifying bot scope/maintenance.

## 3. Fact vs Intent Split

### Code-observed behavior (facts)

- `smmulti` provides persistent-view signup orchestration (owner-only randomizer/preset selection, join/leave, start/cancel).
- `smmulti` persists sessions in `Multiworld` and participants in `MultiworldEntrant`.
- `smmulti` start flow generates seeds via `generate_multiworld(...)`, then DMs each entrant the room URL.
- `doorsmw` manages an external local host service (`localhost:5002`) and exposes operational commands (`host`, `resume`, `kick`, `close`, `forfeit`, `send`, `password`, `msg`) with token/admin checks.
- `bontamw` is currently not loaded in `bot.py` and targets legacy local host service `localhost:5000` using prefix commands.
- `SMZ3Multiworld` model exists but has no active symbol usages in runtime code.
- Shared generator `smz3multi.generate_multiworld(...)` is still used by RaceTime handlers (`smz3`, `smr`) and tournament flow (`tournament/smrl.py`) beyond Discord cogs.

### Owner-confirmed rationale (intent)

- Discord multiworld functionality is being retired as a product decision, not modernized.
- The removal should reduce maintenance and operational scope.
- The deprecation messaging should direct users to the retirement notice (no replacement path).

## 4. Current Workflow (As Implemented)

### 4.1 `smmulti` interactive flow

1. User invokes `/smmulti`.
2. Bot posts an embed + persistent view and creates a `Multiworld` row keyed by message ID.
3. Owner sets randomizer/preset; players join/leave via buttons.
4. Owner starts game; bot validates minimum entrants and generates multiworld seed.
5. Bot DMs each player and marks session closed.

Operational notes:

- Authorization checks are owner-based for setup/start/cancel.
- Entrants are tracked as foreign-key rows under `MultiworldEntrant`.
- Commands currently remain active via extension loading.

### 4.2 `doorsmw` host-control flow

1. User creates host from uploaded multidata.
2. Bot posts host/token/player details embed.
3. Operational slash commands issue control calls to local host service by token.
4. Admin ownership checks gate command execution.

Operational notes:

- Depends on availability/health of local multiworld service endpoint(s).
- Exposes direct administrative actions from Discord into host server command channel.

### 4.3 Disabled legacy `bontamw`

- Prefix commands exist but extension load is commented out.
- Targets legacy port/service and older compatibility assumptions.

## 5. Dependency & Data Surface

Primary Discord-side models/tables:

- `multiworld`
- `multiworldentrant`
- `smz3_multiworld` (legacy)

Discord extension load points:

- Active: `alttprbot_discord.cogs.smmulti`, `alttprbot_discord.cogs.doorsmw`
- Disabled: `alttprbot_discord.cogs.bontamw`

Adjacent dependency surface (important for removal sequencing):

- `alttprbot/alttprgen/smz3multi.py` is shared with RaceTime and tournament modules.
- Removing Discord commands does not automatically remove multiworld generation in RaceTime/tournament paths.

## 6. Deprecation Risks

- User confusion risk if commands are removed without explicit in-command retirement messaging.
- Partial-removal risk if Discord cogs are removed but shared generator assumptions remain undocumented.
- Data drift risk if model/table deletion order is not synchronized with command disablement.
- Operational error exposure while `doorsmw` remains active (external host control from bot commands).

## 7. Deprecation and Removal Plan

### Phase A — Soft Deprecation (current release)

- Keep commands callable but return explicit deprecation/retirement responses with migration pointer text.
- Mark Discord multiworld features as deprecated in operator/developer docs.
- Stop any new feature investment for these components.

### Phase B — Functional Removal (next release)

- Remove extension loading for `smmulti` and `doorsmw` from `alttprbot_discord/bot.py`.
- Remove deprecated command modules (`smmulti.py`, `doorsmw.py`), and keep `bontamw` retired (or delete as dead code).
- Ensure command sync no longer registers retired command groups.

### Phase C — Data Contract Cleanup (next release)

- Remove now-unused model classes: `Multiworld`, `MultiworldEntrant`, `SMZ3Multiworld`.
- Apply migration(s) that drop `multiworld`, `multiworldentrant`, and `smz3_multiworld` per confirmed data policy.
- Remove stale references from docs/context after code and schema removal land.

## 8. Concrete Removal Checklist

- Add deprecation response text for active Discord multiworld commands.
- Announce soft-deprecation window and removal date in bot/operator channels.
- Remove `smmulti` and `doorsmw` extension loads from startup.
- Delete retired cog modules once removal release is cut.
- Drop multiworld-related ORM models and database tables.
- Verify Discord startup, command sync, and non-multiworld generation flows.
- Re-audit RaceTime/tournament multiworld usage if broad multiworld retirement is planned later.

## 9. Migration Target (User Guidance)

Confirmed policy for this deprecation is feature retirement with no replacement workflow.

Recommended deprecation message contract:

- State that Discord multiworld hosting has been retired.
- Clarify no in-bot replacement exists.
- Point users to maintained bot capabilities (non-multiworld generation/tournament/community commands).
