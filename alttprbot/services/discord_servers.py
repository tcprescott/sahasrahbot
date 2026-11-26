"""The Discord server directory: categories of partner servers that a guild posts to its channels.

Each category belongs to a guild and is posted to one channel; each server in it is a
Discord invite code plus the text shown beside it. Categories and the servers in each
are posted in ``order`` (ties by id). Posting (``post``, the website's "Post to
Discord" and ``/discordservers refresh``) deletes SahasrahBot's own messages in each
category's channel and posts every category again, ten servers per message.

The website edits a server's directory (``get_directory`` and the functions after
it); the ``/discordservers`` commands use the older functions. Every function that
takes a ``guild_id`` refuses ids from another guild with ``NotFoundError``.

Checking an invite and posting need Discord. The Discord front end registers both at
startup (``register``); tests and the dev server register fakes.

Callers pass ids and plain values, never Discord objects.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable, Iterable, List, Optional

from alttprbot import models
from alttprbot.exceptions import InvalidInputError, NotFoundError
from alttprbot.services import audit

SERVERS_PER_MESSAGE = 10
TITLE_MAX = 200
DESCRIPTION_MAX = 200
INVITE_MAX = 45

_INVITE_URL = re.compile(r'^(?:https?://)?(?:www\.)?(?:discord(?:app)?\.com/invite|discord\.gg)/', re.IGNORECASE)
_INVITE_CODE = re.compile(r'^[A-Za-z0-9-]+$')


@dataclass(frozen=True)
class ServerListPage:
    """One message of a category's server list."""
    channel_id: int
    category_title: str
    part: int  # 1-based
    part_count: int
    servers: List[models.DiscordServerLists]


@dataclass(frozen=True)
class ServerListLayout:
    """Everything ``refresh`` posts: the channels to clear, then the pages to send, in order."""
    channel_ids: List[int]
    pages: List[ServerListPage]


@dataclass(frozen=True)
class InviteInfo:
    """What Discord says about an invite."""
    code: str
    server_name: str
    member_count: Optional[int] = None
    expires_at: Optional[datetime] = None


@dataclass(frozen=True)
class DirectoryCategory:
    category: models.DiscordServerCategories
    servers: List[models.DiscordServerLists]


@dataclass(frozen=True)
class Directory:
    """A guild's whole directory, in posting order, and whether Discord is up to date."""
    guild_id: int
    categories: List[DirectoryCategory]
    last_posted_at: Optional[datetime]
    unposted_changes: bool


# --- What Discord does for us --------------------------------------------------

InviteLookup = Callable[[str], Awaitable[InviteInfo]]
Poster = Callable[[int, ServerListLayout], Awaitable[None]]

_lookup_invite: Optional[InviteLookup] = None
_poster: Optional[Poster] = None


def register(lookup_invite: InviteLookup, poster: Poster) -> None:
    """``lookup_invite(code)`` returns an ``InviteInfo`` or raises ``InvalidInputError``;
    ``poster(guild_id, layout)`` clears and posts, raising ``InvalidInputError`` with a
    reason a person can read when it can't."""
    global _lookup_invite, _poster
    _lookup_invite = lookup_invite
    _poster = poster


def _require_discord() -> tuple[InviteLookup, Poster]:
    if _lookup_invite is None or _poster is None:
        raise RuntimeError("No Discord registered for the server directory; call alttprbot_discord.gateways.register().")
    return _lookup_invite, _poster


def invite_code(text: str) -> str:
    """The invite code in ``text``: a bare code or a discord.gg / discord.com/invite link."""
    code = _INVITE_URL.sub('', (text or '').strip()).split('?', 1)[0].strip('/')
    if not code or not _INVITE_CODE.match(code) or len(code) > INVITE_MAX:
        raise InvalidInputError("That doesn't look like a Discord invite. Paste a link like https://discord.gg/abc123.")
    return code


async def lookup_invite(text: str) -> InviteInfo:
    """Ask Discord about an invite link or code."""
    lookup, _ = _require_discord()
    return await lookup(invite_code(text))


# --- The /discordservers commands ----------------------------------------------

async def add_category(guild_id: int, channel_id: int, category_title: str,
                       category_description: Optional[str] = None, order: int = 0) -> models.DiscordServerCategories:
    category = await models.DiscordServerCategories.create(
        order=order,
        guild_id=guild_id,
        channel_id=channel_id,
        category_title=category_title,
        category_description=category_description
    )
    await audit.record(audit.SERVER_LIST_CATEGORY_ADDED, target=category_title, guild_id=guild_id,
                       details={'category_id': category.id, 'channel_id': channel_id})
    return category


async def list_categories(guild_id: int) -> List[models.DiscordServerCategories]:
    return await models.DiscordServerCategories.filter(guild_id=guild_id).order_by('order', 'id')


async def _category(guild_id: int, category_id: int) -> models.DiscordServerCategories:
    category = await models.DiscordServerCategories.get_or_none(id=category_id, guild_id=guild_id)
    if category is None:
        raise NotFoundError(f"There's no server list category {category_id} in this server.")
    return category


async def _server(guild_id: int, server_id: int) -> models.DiscordServerLists:
    server = await models.DiscordServerLists.get_or_none(id=server_id, category__guild_id=guild_id)
    if server is None:
        raise NotFoundError(f"There's no server {server_id} in this server's list.")
    return server


async def remove_category(guild_id: int, category_id: int) -> None:
    category = await _category(guild_id, category_id)
    await models.DiscordServerLists.filter(category_id=category_id).delete()
    await category.delete()
    await audit.record(audit.SERVER_LIST_CATEGORY_REMOVED, target=category.category_title,
                       guild_id=guild_id, details={'category_id': category_id})


async def update_category(guild_id: int, category_id: int, category_title: str, category_description: Optional[str],
                          order: Optional[int] = None, channel_id: Optional[int] = None) -> None:
    """Change a category. ``order`` and ``channel_id`` left as None keep what they were."""
    before = await _category(guild_id, category_id)
    after = {
        'title': category_title,
        'description': category_description,
        'order': before.order if order is None else order,
        'channel_id': before.channel_id if channel_id is None else channel_id,
    }
    await models.DiscordServerCategories.filter(id=category_id).update(
        order=after['order'],
        channel_id=after['channel_id'],
        category_title=category_title,
        category_description=category_description
    )
    changed = audit.changes(
        {'title': before.category_title, 'description': before.category_description, 'order': before.order,
         'channel_id': before.channel_id},
        after)
    await audit.record(audit.SERVER_LIST_CATEGORY_UPDATED, target=category_title, guild_id=guild_id,
                       details={'category_id': category_id, 'changes': changed})


async def add_server(guild_id: int, category_id: int, invite_id: str,
                     server_description: str) -> models.DiscordServerLists:
    """Add a server at the end of its category."""
    await _category(guild_id, category_id)
    last = await models.DiscordServerLists.filter(category_id=category_id).order_by('-order').first()
    server = await models.DiscordServerLists.create(
        invite_id=invite_id,
        category_id=category_id,
        server_description=server_description,
        order=last.order + 1 if last else 0,
    )
    await audit.record(audit.SERVER_LIST_SERVER_ADDED, target=server_description or invite_id, guild_id=guild_id,
                       details={'server_id': server.id, 'category_id': category_id, 'invite_id': invite_id})
    return server


async def list_servers(guild_id: int, category_id: int) -> List[models.DiscordServerLists]:
    await _category(guild_id, category_id)
    return await models.DiscordServerLists.filter(category_id=category_id).order_by('order', 'id')


async def remove_server(guild_id: int, server_id: int) -> None:
    server = await _server(guild_id, server_id)
    await server.delete()
    await audit.record(audit.SERVER_LIST_SERVER_REMOVED, target=server.server_description or server.invite_id,
                       guild_id=guild_id, details={'server_id': server_id, 'invite_id': server.invite_id})


async def update_server(guild_id: int, server_id: int, invite_id: str, category_id: int,
                        server_description: Optional[str] = None) -> None:
    """Change a server. A description left as None keeps the old one. Moving it to
    another category puts it at the end there."""
    before = await _server(guild_id, server_id)
    await _category(guild_id, category_id)
    description = before.server_description if server_description is None else server_description
    order = before.order
    if category_id != before.category_id:
        last = await models.DiscordServerLists.filter(category_id=category_id).order_by('-order').first()
        order = last.order + 1 if last else 0
    await models.DiscordServerLists.filter(id=server_id).update(
        invite_id=invite_id,
        category_id=category_id,
        server_description=description,
        order=order,
    )
    changed = audit.changes(
        {'invite_id': before.invite_id, 'category_id': before.category_id,
         'description': before.server_description},
        {'invite_id': invite_id, 'category_id': category_id, 'description': description})
    await audit.record(audit.SERVER_LIST_SERVER_UPDATED, target=description or invite_id,
                       guild_id=guild_id, details={'server_id': server_id, 'changes': changed})


async def server_list_layout(guild_id: int) -> ServerListLayout:
    """The guild's server list split into messages of ``SERVERS_PER_MESSAGE`` servers.

    Categories and servers come in their ``order`` (ties by id). Every category's
    channel is listed in ``channel_ids`` once, even when the category has no servers
    (it is still cleared). A category with no servers gets no page.
    """
    directory = await _categories_with_servers(guild_id)
    channel_ids = list(dict.fromkeys(entry.category.channel_id for entry in directory))

    pages = []
    for entry in directory:
        server_list = entry.servers
        chunks = [server_list[i:i + SERVERS_PER_MESSAGE]
                  for i in range(0, len(server_list), SERVERS_PER_MESSAGE)]
        for idx, servers in enumerate(chunks):
            pages.append(ServerListPage(
                channel_id=entry.category.channel_id,
                category_title=entry.category.category_title,
                part=idx + 1,
                part_count=len(chunks),
                servers=servers,
            ))

    return ServerListLayout(channel_ids=channel_ids, pages=pages)


def page_text(page: ServerListPage) -> str:
    """The message SahasrahBot posts for one page."""
    title = (f"**__{page.category_title}__**" if page.part_count == 1
             else f"**__{page.category_title} - Part {page.part}__**")
    return '\n'.join([title] + [f"{s.server_description}: https://discord.gg/{s.invite_id}" for s in page.servers])


async def post(guild_id: int) -> ServerListLayout:
    """Clear SahasrahBot's messages in the directory's channels and post it again."""
    _, poster = _require_discord()
    layout = await server_list_layout(guild_id)
    if not layout.channel_ids:
        raise InvalidInputError("There's nothing to post yet. Add a category first.")
    await poster(guild_id, layout)
    await audit.record(audit.SERVER_LIST_POSTED, target=f"{len(layout.pages)} messages", guild_id=guild_id,
                       details={'channel_ids': [str(c) for c in layout.channel_ids], 'messages': len(layout.pages)})
    return layout


# --- The website ----------------------------------------------------------------

async def _categories_with_servers(guild_id: int) -> List[DirectoryCategory]:
    categories = await models.DiscordServerCategories.filter(guild_id=guild_id).order_by('order', 'id')
    servers = await models.DiscordServerLists.filter(
        category_id__in=[c.id for c in categories]).order_by('order', 'id') if categories else []
    by_category: dict[int, list] = {c.id: [] for c in categories}
    for server in servers:
        by_category[server.category_id].append(server)
    return [DirectoryCategory(category=c, servers=by_category[c.id]) for c in categories]


async def get_directory(guild_id: int) -> Directory:
    categories = await _categories_with_servers(guild_id)
    entries = models.AuditLog.filter(guild_id=guild_id, action__startswith='server_list.')
    last_posted = await entries.filter(action=audit.SERVER_LIST_POSTED).order_by('-id').first()
    last_change = await entries.exclude(action=audit.SERVER_LIST_POSTED).order_by('-id').first()
    unposted = last_change is not None and (last_posted is None or last_change.id > last_posted.id)
    return Directory(
        guild_id=guild_id,
        categories=categories,
        last_posted_at=last_posted.created_at if last_posted else None,
        unposted_changes=bool(categories) and unposted,
    )


def _text(value: Optional[str], what: str, limit: int, required: bool = True) -> Optional[str]:
    value = (value or '').strip()
    if not value:
        if required:
            raise InvalidInputError(f"Give the {what}.")
        return None
    if len(value) > limit:
        raise InvalidInputError(f"The {what} can be at most {limit} characters.")
    return value


async def create_category(guild_id: int, channel_id: int, title: str, description: Optional[str]) -> None:
    """Add a category at the end of the directory."""
    last = await models.DiscordServerCategories.filter(guild_id=guild_id).order_by('-order').first()
    await add_category(guild_id, channel_id, _text(title, 'title', TITLE_MAX),
                       _text(description, 'note', DESCRIPTION_MAX, required=False),
                       order=last.order + 1 if last else 0)


async def edit_category(guild_id: int, category_id: int, channel_id: int, title: str,
                        description: Optional[str]) -> None:
    await update_category(guild_id, category_id, _text(title, 'title', TITLE_MAX),
                          _text(description, 'note', DESCRIPTION_MAX, required=False), channel_id=channel_id)


async def add_server_from_invite(guild_id: int, category_id: int, invite: str, description: str) -> None:
    """Check the invite with Discord, then add it at the end of the category."""
    description = _text(description, 'text shown in Discord', DESCRIPTION_MAX)
    await _category(guild_id, category_id)
    info = await lookup_invite(invite)
    await add_server(guild_id, category_id, info.code, description)


async def edit_server(guild_id: int, server_id: int, category_id: int, invite: str, description: str) -> None:
    """Change a server; a changed invite is checked with Discord first."""
    description = _text(description, 'text shown in Discord', DESCRIPTION_MAX)
    before = await _server(guild_id, server_id)
    code = invite_code(invite)
    if code != before.invite_id:
        code = (await lookup_invite(code)).code
    await update_server(guild_id, server_id, code, category_id, description)


def _same_ids(given: Iterable[int], existing: Iterable[int], what: str) -> List[int]:
    given = list(given)
    if len(given) != len(set(given)) or set(given) != set(existing):
        raise InvalidInputError(f"The new order has to list each {what} once. Reload the page and try again.")
    return given


async def reorder_categories(guild_id: int, category_ids: List[int]) -> None:
    categories = await models.DiscordServerCategories.filter(guild_id=guild_id)
    ids = _same_ids(category_ids, [c.id for c in categories], 'category')
    for position, category_id in enumerate(ids):
        await models.DiscordServerCategories.filter(id=category_id).update(order=position)
    await audit.record(audit.SERVER_LIST_REORDERED, target='Categories', guild_id=guild_id,
                       details={'category_ids': ids})


async def reorder_servers(guild_id: int, category_id: int, server_ids: List[int]) -> None:
    category = await _category(guild_id, category_id)
    servers = await models.DiscordServerLists.filter(category_id=category_id)
    ids = _same_ids(server_ids, [s.id for s in servers], 'server')
    for position, server_id in enumerate(ids):
        await models.DiscordServerLists.filter(id=server_id).update(order=position)
    await audit.record(audit.SERVER_LIST_REORDERED, target=category.category_title, guild_id=guild_id,
                       details={'category_id': category_id, 'server_ids': ids})
