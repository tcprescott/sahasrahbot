# Plan: Discord Role Assignment Deprecation & Removal

> **Status:** Draft  
> **Last updated:** 2026-02-12  
> **Source design:** [Discord Role Assignment Deprecation Audit](../design/discord_role_assignment_deprecation_audit.md)

## Objective

Retire legacy Discord role automation (reaction-role and voice-role) with low migration risk, explicit admin communication, and clean code/schema removal.

## Scope

In scope:

- `alttprbot_discord/cogs/role.py`
- `alttprbot_discord/cogs/voicerole.py`
- `alttprbot/database/role.py`
- `alttprbot/database/voicerole.py`
- `alttprbot/models/models.py` role-assignment models
- Extension loading and related role-only embed formatting helpers

Out of scope:

- Non-role Discord features
- New replacement feature development (migration target is Discord-native tooling)

## Execution Phases

### Phase A — Soft Deprecation (current release)

- Add explicit deprecation responses to role-assignment command surfaces.
- Publish admin-facing migration guidance to Discord-native role tools.
- Mark feature as deprecated in operator/developer docs.

### Phase B — Functional Disablement (before next release cut)

- Disable reaction/voice runtime listeners.
- Remove extension loading entries after communication window ends.
- Keep clear transitional messaging where command entrypoints remain.

### Phase C — Archive and Removal (next release)

- Export/archive role-assignment tables (`reaction_group`, `reaction_role`, `voice_role`).
- Drop tables and remove model bindings/migrations references as planned.
- Remove deprecated cogs, legacy DB helpers, and role-only embed formatter paths.

## Release Gates

1. **Communication Gate:** admin deprecation message posted before disablement.
2. **Compatibility Gate:** startup and command sync validated after extension removal.
3. **Data Gate:** archive completed before schema drop.
4. **Rollback Gate:** release-level fallback decision documented before destructive migration.

## Concrete Checklist

- Confirm removal release and communication period.
- Implement and verify deprecation command messaging.
- Disable/remove extension loads for role/voicerole cogs.
- Delete deprecated cog and DB helper modules.
- Remove `ReactionGroup`, `ReactionRole`, and `VoiceRole` model classes.
- Apply migration for table drops after archive export.
- Validate bot startup and unaffected command groups.

## Success Criteria

- Role-assignment automation is fully retired from runtime.
- Deprecated data is archived and removed per policy.
- No regressions in non-role Discord surfaces.
