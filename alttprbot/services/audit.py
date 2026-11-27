"""The audit log: who changed what through SahasrahBot, when, where and through what.

Writing an entry
----------------
Services call :func:`record` after a change succeeds::

    await audit.record(audit.ELECTION_CLOSED, target=election.title, guild_id=election.guild_id,
                       details={'election_id': election.id})

Who did it and through what come from the *source* the front end bound before
calling the service (:func:`acting`): the website or ``/api/v1`` (``app_api.py``),
an MCP tool (``mcp/registry.py``), a Discord command or button
(``alttprbot_discord/telemetry.py``, ``alttprbot_discord/audit.py``) or a racetime.gg
chat command (``alttprbot_racetime/telemetry.py``). With no source bound the entry is
SahasrahBot's own doing (``via='system'``): a scheduled job, say. A service that knows
the actor better (a Discord button passes ``user_id``) may pass ``actor_discord_id``.

Every action is a constant here with a label in ``ACTIONS``; :func:`record` refuses an
unknown one, and ``tests/test_audit.py`` checks each has an area. ``details`` is plain
JSON data: ids, and ``{'changes': {field: [old, new]}}`` for edits. Never secrets,
never a ballot's choices, never message text.

Entries are kept forever. Purging an account clears the actor's id and name on their
entries (:func:`forget_actor`), so the trail stays without naming them.

Reading it
----------
:func:`list_entries` applies who may see what: everyone sees their own actions
(``mine``), a server's Administrators see that server's entries, and the bot's owners
(plus ``config.AUDIT_LOG_VIEWER_IDS``) see everything (``all``).
"""

import logging
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Iterator, Optional

from tortoise.expressions import Q

import config
from alttprbot import models
from alttprbot.exceptions import InvalidInputError, PermissionDeniedError
from alttprbot.services import discord_directory

logger = logging.getLogger(__name__)

# --- Where a change came from ---------------------------------------------------

VIA_WEBSITE = 'website'
VIA_API = 'api'
VIA_MCP = 'mcp'
VIA_DISCORD = 'discord'
VIA_RACETIME = 'racetime'
VIA_SYSTEM = 'system'
VIAS = {
    VIA_WEBSITE: 'Website',
    VIA_API: 'API token',
    VIA_MCP: 'AI client',
    VIA_DISCORD: 'Discord',
    VIA_RACETIME: 'racetime.gg',
    VIA_SYSTEM: 'SahasrahBot',
}


@dataclass(frozen=True)
class Source:
    """Who is acting and through what. ``detail`` names the token, AI client or command."""

    via: str
    detail: Optional[str] = None
    actor_discord_id: Optional[int] = None
    actor_name: Optional[str] = None
    racetime_id: Optional[str] = None


SYSTEM = Source(via=VIA_SYSTEM)
_source: ContextVar[Source] = ContextVar('audit_source', default=SYSTEM)


def set_source(source: Source) -> Token:
    return _source.set(source)


def reset_source(token: Token) -> None:
    _source.reset(token)


def current_source() -> Source:
    return _source.get()


@contextmanager
def acting(source: Source) -> Iterator[Source]:
    """Bind ``source`` for the changes made inside the block."""
    token = _source.set(source)
    try:
        yield source
    finally:
        _source.reset(token)


# --- What can be recorded -------------------------------------------------------

ELECTION_CREATED = 'election.created'
ELECTION_UPDATED = 'election.updated'
ELECTION_PUBLISHED = 'election.published'
ELECTION_CLOSED = 'election.closed'
ELECTION_DELETED = 'election.deleted'
ELECTION_VOTED = 'election.voted'
PRESET_CREATED = 'preset.created'
PRESET_UPDATED = 'preset.updated'
PRESET_DELETED = 'preset.deleted'
TRIFORCE_TEXT_SUBMITTED = 'triforce_text.submitted'
TRIFORCE_TEXT_APPROVED = 'triforce_text.approved'
TRIFORCE_TEXT_REJECTED = 'triforce_text.rejected'
SERVER_SETTING_CHANGED = 'server_setting.changed'
SERVER_SETTING_REMOVED = 'server_setting.removed'
# reaction_group.* / reaction_role.*: the old reaction roles, kept so old entries keep their labels.
REACTION_GROUP_CREATED = 'reaction_group.created'
REACTION_GROUP_UPDATED = 'reaction_group.updated'
REACTION_GROUP_DELETED = 'reaction_group.deleted'
REACTION_ROLE_CREATED = 'reaction_role.created'
REACTION_ROLE_UPDATED = 'reaction_role.updated'
REACTION_ROLE_DELETED = 'reaction_role.deleted'
ROLE_MENU_CREATED = 'role_menu.created'
ROLE_MENU_UPDATED = 'role_menu.updated'
ROLE_MENU_REPOSTED = 'role_menu.reposted'
ROLE_MENU_DELETED = 'role_menu.deleted'
VOICE_ROLE_CREATED = 'voice_role.created'
VOICE_ROLE_DELETED = 'voice_role.deleted'
SERVER_LIST_CATEGORY_ADDED = 'server_list.category_added'
SERVER_LIST_CATEGORY_UPDATED = 'server_list.category_updated'
SERVER_LIST_CATEGORY_REMOVED = 'server_list.category_removed'
SERVER_LIST_SERVER_ADDED = 'server_list.server_added'
SERVER_LIST_SERVER_UPDATED = 'server_list.server_updated'
SERVER_LIST_SERVER_REMOVED = 'server_list.server_removed'
SERVER_LIST_REORDERED = 'server_list.reordered'
SERVER_LIST_POSTED = 'server_list.posted'
RACER_VERIFICATION_CONFIGURED = 'racer_verification.configured'
RACER_VERIFICATION_VERIFIED = 'racer_verification.verified'
INQUIRY_CREATED = 'inquiry.created'
INQUIRY_REMOVED = 'inquiry.removed'
INQUIRY_LOCATED = 'inquiry.located'
API_TOKEN_CREATED = 'api_token.created'
API_TOKEN_REVOKED = 'api_token.revoked'
AI_CLIENT_CONNECTED = 'ai_client.connected'
AI_CLIENT_DISCONNECTED = 'ai_client.disconnected'
ACCOUNT_RACETIME_LINKED = 'account.racetime_linked'
ACCOUNT_PURGED = 'account.purged'
TOURNAMENT_SETTINGS_SUBMITTED = 'tournament.settings_submitted'
MULTIWORLD_CREATED = 'multiworld.created'
MULTIWORLD_STARTED = 'multiworld.started'
MULTIWORLD_CANCELLED = 'multiworld.cancelled'

# Every action, with how the audit log page names it.
ACTIONS: dict[str, str] = {
    ELECTION_CREATED: 'Created an election',
    ELECTION_UPDATED: 'Edited an election',
    ELECTION_PUBLISHED: 'Posted an election',
    ELECTION_CLOSED: 'Closed an election',
    ELECTION_DELETED: 'Deleted an election',
    ELECTION_VOTED: 'Voted in an election',
    PRESET_CREATED: 'Created a preset',
    PRESET_UPDATED: 'Edited a preset',
    PRESET_DELETED: 'Deleted a preset',
    TRIFORCE_TEXT_SUBMITTED: 'Submitted a triforce text',
    TRIFORCE_TEXT_APPROVED: 'Approved a triforce text',
    TRIFORCE_TEXT_REJECTED: 'Rejected a triforce text',
    SERVER_SETTING_CHANGED: 'Changed a server setting',
    SERVER_SETTING_REMOVED: 'Removed a server setting',
    REACTION_GROUP_CREATED: 'Created a reaction role menu',
    REACTION_GROUP_UPDATED: 'Edited a reaction role menu',
    REACTION_GROUP_DELETED: 'Deleted a reaction role menu',
    REACTION_ROLE_CREATED: 'Added a reaction role',
    REACTION_ROLE_UPDATED: 'Edited a reaction role',
    REACTION_ROLE_DELETED: 'Removed a reaction role',
    ROLE_MENU_CREATED: 'Created a role menu',
    ROLE_MENU_UPDATED: 'Edited a role menu',
    ROLE_MENU_REPOSTED: 'Reposted a role menu',
    ROLE_MENU_DELETED: 'Deleted a role menu',
    VOICE_ROLE_CREATED: 'Added a voice channel role',
    VOICE_ROLE_DELETED: 'Removed a voice channel role',
    SERVER_LIST_CATEGORY_ADDED: 'Added a server list category',
    SERVER_LIST_CATEGORY_UPDATED: 'Edited a server list category',
    SERVER_LIST_CATEGORY_REMOVED: 'Removed a server list category',
    SERVER_LIST_SERVER_ADDED: 'Added a server to a server list',
    SERVER_LIST_SERVER_UPDATED: 'Edited a server in a server list',
    SERVER_LIST_SERVER_REMOVED: 'Removed a server from a server list',
    SERVER_LIST_REORDERED: 'Reordered a server list',
    SERVER_LIST_POSTED: 'Posted a server list to Discord',
    RACER_VERIFICATION_CONFIGURED: 'Set up racer verification',
    RACER_VERIFICATION_VERIFIED: 'Was verified as a racer',
    INQUIRY_CREATED: 'Set up an inquiry message',
    INQUIRY_REMOVED: 'Removed an inquiry message',
    INQUIRY_LOCATED: 'Found where an older inquiry message is',
    API_TOKEN_CREATED: 'Made an API token',
    API_TOKEN_REVOKED: 'Revoked an API token',
    AI_CLIENT_CONNECTED: 'Connected an AI client',
    AI_CLIENT_DISCONNECTED: 'Disconnected an AI client',
    ACCOUNT_RACETIME_LINKED: 'Linked a racetime.gg account',
    ACCOUNT_PURGED: 'Deleted their SahasrahBot data',
    TOURNAMENT_SETTINGS_SUBMITTED: 'Submitted tournament settings',
    MULTIWORLD_CREATED: 'Opened a multiworld',
    MULTIWORLD_STARTED: 'Started a multiworld',
    MULTIWORLD_CANCELLED: 'Cancelled a multiworld',
}

# The Area filter: an action's prefix (before the dot) decides its area.
AREAS: dict[str, tuple[str, tuple[str, ...]]] = {
    'elections': ('Elections', ('election',)),
    'presets': ('Presets', ('preset',)),
    'triforce_texts': ('Triforce texts', ('triforce_text',)),
    'server': ('Server settings and roles', ('server_setting', 'reaction_group', 'reaction_role', 'role_menu', 'voice_role',
                                             'server_list', 'racer_verification', 'inquiry')),
    'tokens': ('Tokens and AI clients', ('api_token', 'ai_client')),
    'accounts': ('Accounts', ('account',)),
    'tournaments': ('Tournaments', ('tournament',)),
    'multiworld': ('Multiworld', ('multiworld',)),
}


def area_of(action: str) -> Optional[str]:
    prefix = action.split('.', 1)[0]
    return next((key for key, (_, prefixes) in AREAS.items() if prefix in prefixes), None)


def changes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list]:
    """``{field: [old, new]}`` for each field whose value differs, for ``details['changes']``."""
    return {k: [_plain(before.get(k)), _plain(after.get(k))] for k in after if before.get(k) != after.get(k)}


def _plain(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    return str(value)


def _clip(value: Optional[str], length: int) -> Optional[str]:
    if value is None:
        return None
    value = str(value)
    return value if len(value) <= length else value[:length - 1] + '…'


async def _actor_from_racetime(racetime_id: str) -> Optional[int]:
    user = await models.Users.get_or_none(rtgg_id=racetime_id)
    return user.discord_user_id if user else None


async def record(action: str, *, target: Optional[str] = None, guild_id: Optional[int] = None,
                 details: Optional[dict] = None, actor_discord_id: Optional[int] = None,
                 actor_name: Optional[str] = None) -> None:
    """Write an audit entry for a change that has happened.

    Never raises for a database problem (the change already happened; the failure is
    logged at ERROR, so Sentry sees it). An unknown ``action`` is a bug and raises."""
    if action not in ACTIONS:
        raise ValueError(f"Unknown audit action {action!r}: add it to audit.ACTIONS.")
    source = current_source()
    try:
        if actor_discord_id is not None and actor_discord_id != source.actor_discord_id:
            actor_id, name = actor_discord_id, actor_name
        else:
            actor_id, name = source.actor_discord_id, actor_name or source.actor_name
            if actor_id is None and source.racetime_id:
                actor_id = await _actor_from_racetime(source.racetime_id)
        if name is None and actor_id is not None:
            user = await models.Users.get_or_none(discord_user_id=actor_id)
            name = user.display_name if user else None
        await models.AuditLog.create(
            action=action,
            actor_discord_id=actor_id,
            actor_name=_clip(name, 100),
            via=source.via,
            via_detail=_clip(source.detail, 200),
            guild_id=guild_id,
            target=_clip(target, 300),
            details=_plain(details) if details else None,
        )
    except Exception:
        logger.exception("Couldn't write the audit entry %s", action)


async def forget_actor(discord_user_id: int) -> None:
    """Unlink a purged account from its entries: they stay, without naming the person."""
    await models.AuditLog.filter(actor_discord_id=discord_user_id).update(actor_discord_id=None, actor_name=None)


# --- Who may read what ----------------------------------------------------------

SCOPE_MINE = 'mine'
SCOPE_ALL = 'all'
PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
EXPORT_LIMIT = 10000


async def can_see_everything(user_id: int) -> bool:
    if user_id in set(getattr(config, 'AUDIT_LOG_VIEWER_IDS', None) or ()):
        return True
    try:
        return await discord_directory.get().is_owner(user_id)
    except RuntimeError:
        return False


async def scopes(user_id: int, admin_guild_ids: Iterable[int]) -> list[dict]:
    """What the viewer can pick in "Showing": their own activity, each server they
    administer that the bot is in, and everything if they own the bot."""
    result = [{'key': SCOPE_MINE, 'label': 'My activity'}]
    try:
        guilds = await discord_directory.get().bot_guilds(admin_guild_ids)
    except RuntimeError:
        guilds = []
    result += [{'key': str(g.id), 'label': g.name} for g in guilds]
    if await can_see_everything(user_id):
        result.append({'key': SCOPE_ALL, 'label': 'Everything'})
    return result


def areas() -> list[dict]:
    return [{'key': key, 'label': label} for key, (label, _) in AREAS.items()]


async def _scope_filter(user_id: int, admin_guild_ids: Iterable[int], scope: str) -> Q:
    if scope == SCOPE_MINE:
        return Q(actor_discord_id=user_id)
    if scope == SCOPE_ALL:
        if not await can_see_everything(user_id):
            raise PermissionDeniedError("Only the bot's owners can see everyone's activity.")
        return Q()
    try:
        guild_id = int(scope)
    except ValueError:
        raise InvalidInputError("That isn't a server or an audit log scope.") from None
    if guild_id not in set(admin_guild_ids) and not await can_see_everything(user_id):
        raise PermissionDeniedError("You can only see the audit log of servers you administer.")
    return Q(guild_id=guild_id)


def _search_filter(query: str) -> Q:
    text = query.strip().lower()
    matched = [action for action, label in ACTIONS.items() if text in label.lower() or text in action]
    q = Q(target__icontains=text) | Q(actor_name__icontains=text) | Q(via_detail__icontains=text)
    if matched:
        q |= Q(action__in=matched)
    return q


@dataclass(frozen=True)
class Filters:
    scope: str = SCOPE_MINE
    area: Optional[str] = None
    query: Optional[str] = None
    actor_discord_id: Optional[int] = None
    before_id: Optional[int] = None
    limit: int = PAGE_SIZE


async def _filtered(user_id: int, admin_guild_ids: Iterable[int], filters: Filters):
    q = await _scope_filter(user_id, admin_guild_ids, filters.scope)
    if filters.area:
        if filters.area not in AREAS:
            raise InvalidInputError("That isn't an audit log area.")
        q &= Q(action__in=[a for a in ACTIONS if area_of(a) == filters.area])
    if filters.query and filters.query.strip():
        q &= _search_filter(filters.query)
    if filters.actor_discord_id is not None:
        q &= Q(actor_discord_id=filters.actor_discord_id)
    if filters.before_id is not None:
        q &= Q(id__lt=filters.before_id)
    return models.AuditLog.filter(q).order_by('-id')


async def _guild_names(guild_ids: Iterable[int]) -> dict[int, str]:
    ids = {g for g in guild_ids if g is not None}
    if not ids:
        return {}
    try:
        return {g.id: g.name for g in await discord_directory.get().bot_guilds(ids)}
    except RuntimeError:
        return {}


def _entry(row: models.AuditLog, guild_names: dict[int, str]) -> dict:
    return {
        'id': row.id,
        'created_at': row.created_at,
        'action': row.action,
        'label': ACTIONS.get(row.action, row.action),
        'area': area_of(row.action),
        'actor_id': row.actor_discord_id,
        'actor_name': row.actor_name,
        'via': row.via,
        'via_label': VIAS.get(row.via, row.via),
        'via_detail': row.via_detail,
        'guild_id': row.guild_id,
        'guild_name': guild_names.get(row.guild_id) if row.guild_id else None,
        'target': row.target,
        'details': row.details or {},
    }


async def list_entries(user_id: int, admin_guild_ids: Iterable[int], filters: Filters) -> dict:
    """A page of entries the viewer may see, newest first, with the cursor for the next page."""
    admin = frozenset(admin_guild_ids)
    limit = max(1, min(filters.limit, MAX_PAGE_SIZE))
    rows = await (await _filtered(user_id, admin, filters)).limit(limit + 1)
    more = len(rows) > limit
    rows = rows[:limit]
    names = await _guild_names(r.guild_id for r in rows)
    return {
        'entries': [_entry(r, names) for r in rows],
        'next_before': rows[-1].id if more and rows else None,
    }


async def export_entries(user_id: int, admin_guild_ids: Iterable[int], filters: Filters) -> list[dict]:
    """Every entry matching ``filters`` (up to ``EXPORT_LIMIT``), for the CSV export."""
    admin = frozenset(admin_guild_ids)
    rows = await (await _filtered(user_id, admin, Filters(
        scope=filters.scope, area=filters.area, query=filters.query,
        actor_discord_id=filters.actor_discord_id))).limit(EXPORT_LIMIT)
    names = await _guild_names(r.guild_id for r in rows)
    return [_entry(r, names) for r in rows]
