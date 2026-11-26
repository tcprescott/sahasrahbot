"""Role menus: Discord messages people use to give themselves roles.

A menu is a message in a channel with a title, a description and up to 25 roles.
Each menu has a style, chosen by an admin:

- ``reactions``: react with a role's emoji to get it, remove the reaction to lose it
  (up to 20 roles: Discord's reaction limit).
- ``buttons``: one button per role; pressing it adds or removes the role and answers
  the person privately.
- ``dropdown``: one dropdown listing every role; picking one adds or removes it.

A menu with ``single_choice`` lets a person hold one of its roles at a time.

Menus that came from the old reaction roles on someone else's message
(``posted_by_bot`` false) can only use reactions, since the bot can't edit that
message; reposting one moves it to a message the bot posts.

Admins are the server's Administrators and the bot owner, the same as elections.
The website, the MCP server and Discord all go through here. Discord itself is
reached through the gateway that ``alttprbot_discord/role_menus.py`` registers.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Iterable, Optional, Protocol

from tortoise.transactions import in_transaction

from alttprbot import models
from alttprbot.exceptions import InvalidInputError, NotFoundError, PermissionDeniedError
from alttprbot.services import audit, discord_directory
from alttprbot.services import servers as server_access
from alttprbot.services.discord_directory import Named

logger = logging.getLogger(__name__)

REACTIONS, BUTTONS, DROPDOWN = 'reactions', 'buttons', 'dropdown'
STYLES = (REACTIONS, BUTTONS, DROPDOWN)
STYLE_LABELS = {REACTIONS: 'Reactions', BUTTONS: 'Buttons', DROPDOWN: 'Dropdown'}
MAX_OPTIONS = {REACTIONS: 20, BUTTONS: 25, DROPDOWN: 25}

MAX_TITLE = 256
MAX_DESCRIPTION = 4000
MAX_LABEL = 80
MAX_OPTION_DESCRIPTION = 100  # what a dropdown option can show
MAX_EMOJI = 100

_CUSTOM_EMOJI = re.compile(r'^<?(?P<animated>a)?:(?P<name>[A-Za-z0-9_~]{2,32}):(?P<id>\d{1,25})>?$')
_VARIATION_SELECTOR = '️'


# --- Discord, as the services see it -----------------------------------------------


@dataclass(frozen=True)
class ServerRole:
    id: int
    name: str
    # Whether the bot can give it: below the bot's highest role, and the bot has Manage Roles.
    assignable: bool


@dataclass(frozen=True)
class ServerDetails:
    channels: list[Named]
    roles: list[ServerRole]
    # Custom emoji in the server, as ``<:name:id>``.
    emojis: list[Named]


class RoleMenuDiscord(Protocol):
    async def server(self, guild_id: int) -> Optional[ServerDetails]:
        """Channels the bot can post in, roles and custom emoji; None if the bot isn't there."""

    async def publish(self, menu: dict) -> int:
        """Post the menu (``view()``), or redraw it in place when it has a message, and
        return the message id. Posts a new message if a bot-posted one was deleted.
        Raises ``InvalidInputError`` with a readable reason when Discord refuses."""

    async def remove(self, menu: dict) -> None:
        """Take the menu off Discord: delete the bot's message, or for a menu on someone
        else's message remove the bot's reactions. Best effort."""


_discord: Optional[RoleMenuDiscord] = None


def register(gateway: RoleMenuDiscord) -> None:
    global _discord
    _discord = gateway


def _gateway() -> RoleMenuDiscord:
    if _discord is None:
        raise RuntimeError("No role menu gateway registered; call alttprbot_discord.gateways.register() at startup.")
    return _discord


# --- emoji ----------------------------------------------------------------------------


def clean_emoji(text: Optional[str]) -> Optional[str]:
    """An emoji as stored: ``<:name:id>`` / ``<a:name:id>`` for a custom one (also
    accepted as ``:name:id`` or ``name:id``), else the Unicode text. None for blank."""
    text = (text or '').strip()
    if not text:
        return None
    match = _CUSTOM_EMOJI.match(text) or _CUSTOM_EMOJI.match(f':{text}')
    if match:
        prefix = 'a' if match['animated'] else ''
        return f"<{prefix}:{match['name']}:{match['id']}>"
    if len(text) > 20 or any(c.isspace() for c in text) or text.isascii():
        raise InvalidInputError(f"“{text[:40]}” isn't an emoji. Use an emoji, or a custom one as <:name:id>.")
    return text


def emoji_key(text: Optional[str]) -> Optional[str]:
    """What two emoji are compared by: a custom emoji's id (so renaming it doesn't
    matter), else the Unicode text without variation selectors."""
    if not text:
        return None
    match = _CUSTOM_EMOJI.match(text.strip())
    if match:
        return match['id']
    return text.strip().replace(_VARIATION_SELECTOR, '')


# --- who may do what -------------------------------------------------------------------


async def is_admin(guild_id: int, user_id: int) -> bool:
    return await server_access.is_admin(guild_id, user_id)


async def _require_admin(guild_id: int, user_id: int) -> None:
    await server_access.require_admin(guild_id, user_id)


async def _admin_menu(menu_id: int, user_id: int) -> models.RoleMenu:
    menu = await models.RoleMenu.get_or_none(id=menu_id)
    if menu is None:
        raise NotFoundError("That role menu doesn't exist.")
    await _require_admin(menu.guild_id, user_id)
    return menu


async def servers(admin_guild_ids: Iterable[int]) -> list[dict]:
    """The servers someone can make role menus in: those of ``admin_guild_ids`` the bot is in."""
    return [{'id': g.id, 'name': g.name} for g in await discord_directory.get().bot_guilds(admin_guild_ids)]


async def server_options(guild_id: int, user_id: int) -> dict:
    """The channels, roles and custom emoji the editor offers for a server."""
    await _require_admin(guild_id, user_id)
    details = await _gateway().server(guild_id)
    if details is None:
        raise NotFoundError("SahasrahBot isn't in that server.")
    return {
        'channels': [{'id': c.id, 'name': c.name} for c in details.channels],
        'roles': [{'id': r.id, 'name': r.name, 'assignable': r.assignable} for r in details.roles],
        'emojis': [{'id': e.id, 'name': e.name} for e in details.emojis],
    }


# --- reading ---------------------------------------------------------------------------


async def _options(menu: models.RoleMenu) -> list[models.RoleMenuOption]:
    return await models.RoleMenuOption.filter(menu_id=menu.id).order_by('position', 'id')


def view(menu: models.RoleMenu, options: list[models.RoleMenuOption]) -> dict:
    """A menu as plain data, for Discord and the API."""
    return {
        'id': menu.id,
        'guild_id': menu.guild_id,
        'channel_id': menu.channel_id,
        'message_id': menu.message_id,
        'title': menu.title,
        'description': menu.description,
        'style': menu.style,
        'posted_by_bot': menu.posted_by_bot,
        'single_choice': menu.single_choice,
        'options': [{'id': o.id, 'role_id': o.role_id, 'label': o.label, 'description': o.description,
                     'emoji': o.emoji} for o in options],
    }


def problems(menu: dict, details: Optional[ServerDetails]) -> list[str]:
    """What will stop the menu working, as sentences for the admin."""
    if details is None:
        return ["SahasrahBot isn't in this server any more."]
    found = []
    channels = {c.id for c in details.channels}
    if menu['channel_id'] not in channels:
        found.append("SahasrahBot can't post in this menu's channel, or the channel was deleted.")
    roles = {r.id: r for r in details.roles}
    for option in menu['options']:
        role = roles.get(option['role_id'])
        if role is None:
            found.append(f"The role for “{option['label']}” was deleted.")
        elif not role.assignable:
            found.append(f"SahasrahBot can't give {role.name}: it's above SahasrahBot's highest role, "
                         "or SahasrahBot doesn't have Manage Roles.")
    return found


def _enrich(menu: dict, details: Optional[ServerDetails], guild_name: Optional[str]) -> dict:
    channels = {c.id: c.name for c in details.channels} if details else {}
    roles = {r.id: r.name for r in details.roles} if details else {}
    return {
        **menu,
        'guild_name': guild_name,
        'channel_name': channels.get(menu['channel_id']),
        'options': [{**o, 'role_name': roles.get(o['role_id'])} for o in menu['options']],
        'problems': problems(menu, details),
    }


async def list_menus(admin_guild_ids: Iterable[int]) -> list[dict]:
    """Every menu in the servers of ``admin_guild_ids`` the bot is in, by server then title."""
    guilds = {g.id: g.name for g in await discord_directory.get().bot_guilds(admin_guild_ids)}
    if not guilds:
        return []
    menus = await models.RoleMenu.filter(guild_id__in=list(guilds)).prefetch_related('options')
    details = {gid: await _gateway().server(gid) for gid in {m.guild_id for m in menus}}
    found = [_enrich(view(m, sorted(m.options, key=lambda o: (o.position, o.id))), details[m.guild_id],
                     guilds[m.guild_id]) for m in menus]
    return sorted(found, key=lambda m: ((m['guild_name'] or '').casefold(), m['title'].casefold(), m['id']))


async def get_menu(menu_id: int, user_id: int) -> dict:
    menu = await _admin_menu(menu_id, user_id)
    details = await _gateway().server(menu.guild_id)
    return _enrich(view(menu, await _options(menu)), details,
                   await discord_directory.get().guild_name(menu.guild_id))


async def menus_in_guild(guild_id: int) -> list[dict]:
    """A server's menus, for the Discord command. Callers check permissions."""
    menus = await models.RoleMenu.filter(guild_id=guild_id).order_by('title', 'id').prefetch_related('options')
    return [view(m, sorted(m.options, key=lambda o: (o.position, o.id))) for m in menus]


# --- writing -----------------------------------------------------------------------------


@dataclass
class OptionInput:
    role_id: int
    label: str
    emoji: Optional[str] = None
    description: Optional[str] = None
    # An existing option's id, to keep it; None adds one.
    id: Optional[int] = None


@dataclass
class MenuInput:
    guild_id: int
    channel_id: int
    title: str
    description: Optional[str] = None
    style: str = BUTTONS
    single_choice: bool = False
    options: list[OptionInput] = field(default_factory=list)


def _clean(data: MenuInput, *, posted_by_bot: bool) -> MenuInput:
    """Checked and tidied input. Raises ``InvalidInputError`` with every problem."""
    errors = []
    title = (data.title or '').strip()
    description = (data.description or '').strip() or None
    if not title:
        errors.append("Give the menu a title.")
    elif len(title) > MAX_TITLE:
        errors.append(f"The title can be at most {MAX_TITLE} characters.")
    if description and len(description) > MAX_DESCRIPTION:
        errors.append(f"The description can be at most {MAX_DESCRIPTION} characters.")
    if data.style not in STYLES:
        errors.append("Pick reactions, buttons or a dropdown.")
    elif not posted_by_bot and data.style != REACTIONS:
        errors.append("This menu is on a message SahasrahBot didn't post, so it can only use reactions. "
                      "Repost it to use buttons or a dropdown.")
    if not data.options:
        errors.append("Add at least one role.")
    limit = MAX_OPTIONS.get(data.style, 25)
    if len(data.options) > limit:
        errors.append(f"A {STYLE_LABELS.get(data.style, '').lower()} menu can have at most {limit} roles.")

    options, seen_roles, seen_emoji = [], set(), set()
    for n, option in enumerate(data.options, start=1):
        label = (option.label or '').strip()
        name = f"“{label}”" if label else f"Role {n}"
        try:
            emoji = clean_emoji(option.emoji)
        except InvalidInputError as e:
            errors.append(f"{name}: {e}")
            emoji = None
        option_description = (option.description or '').strip() or None
        if not label:
            errors.append(f"Role {n} needs a label.")
        elif len(label) > MAX_LABEL:
            errors.append(f"{name}: a label can be at most {MAX_LABEL} characters.")
        if option_description and len(option_description) > MAX_OPTION_DESCRIPTION:
            errors.append(f"{name}: a description can be at most {MAX_OPTION_DESCRIPTION} characters.")
        if data.style == REACTIONS and not emoji and not option.emoji:
            errors.append(f"{name} needs an emoji: people react with it.")
        if option.role_id in seen_roles:
            errors.append(f"{name}: that role is already on this menu.")
        seen_roles.add(option.role_id)
        key = emoji_key(emoji)
        if key and key in seen_emoji:
            errors.append(f"{name}: that emoji is already on this menu.")
        if key:
            seen_emoji.add(key)
        options.append(OptionInput(role_id=option.role_id, label=label, emoji=emoji,
                                   description=option_description, id=option.id))
    if errors:
        raise InvalidInputError(' '.join(errors))
    return MenuInput(guild_id=data.guild_id, channel_id=data.channel_id, title=title, description=description,
                     style=data.style, single_choice=bool(data.single_choice), options=options)


async def _check_targets(data: MenuInput) -> None:
    details = await _gateway().server(data.guild_id)
    if details is None:
        raise InvalidInputError("SahasrahBot isn't in that server.")
    if data.channel_id not in {c.id for c in details.channels}:
        raise InvalidInputError("SahasrahBot can't post in that channel. It needs View Channel, Send Messages, "
                                "Embed Links and Add Reactions there.")
    roles = {r.id: r for r in details.roles}
    for option in data.options:
        role = roles.get(option.role_id)
        if role is None:
            raise InvalidInputError(f"“{option.label}”: pick a role from this server.")
        if not role.assignable:
            raise InvalidInputError(f"SahasrahBot can't give {role.name}. Move SahasrahBot's role above it in "
                                    "Server Settings > Roles, and make sure SahasrahBot has Manage Roles.")


async def _save_options(menu: models.RoleMenu, options: list[OptionInput]) -> None:
    existing = {o.id: o for o in await models.RoleMenuOption.filter(menu_id=menu.id)}
    keep = set()
    for position, option in enumerate(options):
        values = {'role_id': option.role_id, 'label': option.label, 'emoji': option.emoji,
                  'description': option.description, 'position': position}
        row = existing.get(option.id) if option.id is not None else None
        if row is not None:
            row.update_from_dict(values)
            await row.save()
            keep.add(row.id)
        else:
            await models.RoleMenuOption.create(menu_id=menu.id, **values)
    gone = [oid for oid in existing if oid not in keep]
    if gone:
        await models.RoleMenuOption.filter(id__in=gone).delete()


def _audit_fields(menu: dict) -> dict:
    return {
        'title': menu['title'],
        'description': menu['description'],
        'style': menu['style'],
        'channel_id': str(menu['channel_id']),
        'single_choice': menu['single_choice'],
        'roles': [f"{o['emoji'] + ' ' if o['emoji'] else ''}{o['label']} ({o['role_id']})" for o in menu['options']],
    }


async def _publish(menu: models.RoleMenu) -> dict:
    """Post or redraw the menu on Discord and remember its message."""
    current = view(menu, await _options(menu))
    message_id = await _gateway().publish(current)
    if message_id != menu.message_id:
        menu.message_id = message_id
        await menu.save(update_fields=['message_id'])
        current['message_id'] = message_id
    _forget_reaction_messages()
    return current


async def create_menu(user_id: int, data: MenuInput) -> dict:
    """Save a menu and post it. Nothing is kept if posting fails."""
    await _require_admin(data.guild_id, user_id)
    data = _clean(data, posted_by_bot=True)
    await _check_targets(data)
    async with in_transaction():
        menu = await models.RoleMenu.create(guild_id=data.guild_id, channel_id=data.channel_id, title=data.title,
                                            description=data.description, style=data.style,
                                            single_choice=data.single_choice, posted_by_bot=True)
        await _save_options(menu, data.options)
    try:
        posted = await _publish(menu)
    except Exception:
        await menu.delete()
        raise
    await audit.record(audit.ROLE_MENU_CREATED, target=data.title, guild_id=data.guild_id,
                       details={'role_menu_id': menu.id, **_audit_fields(posted)})
    return await get_menu(menu.id, user_id)


async def update_menu(menu_id: int, user_id: int, data: MenuInput) -> dict:
    """Change a menu and redraw it. Moving a bot-posted menu to another channel posts
    it there and deletes the old message."""
    menu = await _admin_menu(menu_id, user_id)
    if data.guild_id != menu.guild_id:
        raise InvalidInputError("A role menu stays in its server.")
    data = _clean(data, posted_by_bot=menu.posted_by_bot)
    if not menu.posted_by_bot and data.channel_id != menu.channel_id:
        raise InvalidInputError("This menu is on a message SahasrahBot didn't post, so it can't move. "
                                "Repost it to put it in another channel.")
    await _check_targets(data)
    before = view(menu, await _options(menu))
    moving = data.channel_id != menu.channel_id
    async with in_transaction():
        menu.update_from_dict({'channel_id': data.channel_id, 'title': data.title, 'description': data.description,
                               'style': data.style, 'single_choice': data.single_choice})
        if moving:
            menu.message_id = None
        await menu.save()
        await _save_options(menu, data.options)
    if moving:
        await _gateway().remove(before)
    after = await _publish(menu)
    changed = audit.changes(_audit_fields(before), _audit_fields(after))
    if changed:
        await audit.record(audit.ROLE_MENU_UPDATED, target=menu.title, guild_id=menu.guild_id,
                           details={'role_menu_id': menu.id, 'changes': changed})
    return await get_menu(menu.id, user_id)


async def repost(menu_id: int, user_id: int) -> dict:
    """Post the menu as a new message. The bot's old message is deleted; a menu on
    someone else's message loses the bot's reactions there and becomes the bot's."""
    menu = await _admin_menu(menu_id, user_id)
    before = view(menu, await _options(menu))
    await _gateway().remove(before)
    menu.message_id = None
    menu.posted_by_bot = True
    await menu.save(update_fields=['message_id', 'posted_by_bot'])
    await _publish(menu)
    await audit.record(audit.ROLE_MENU_REPOSTED, target=menu.title, guild_id=menu.guild_id,
                       details={'role_menu_id': menu.id, 'channel_id': str(menu.channel_id)})
    return await get_menu(menu.id, user_id)


async def delete_menu(menu_id: int, user_id: int) -> None:
    """Delete the menu and take it off Discord. Roles people already have stay."""
    menu = await _admin_menu(menu_id, user_id)
    before = view(menu, await _options(menu))
    await _gateway().remove(before)
    await menu.delete()
    _forget_reaction_messages()
    await audit.record(audit.ROLE_MENU_DELETED, target=menu.title, guild_id=menu.guild_id,
                       details={'role_menu_id': menu.id, **_audit_fields(before)})


# --- people picking roles ---------------------------------------------------------------

# The messages that are reaction menus, so a reaction anywhere else costs no query.
_reaction_messages: Optional[frozenset[int]] = None


def _forget_reaction_messages() -> None:
    global _reaction_messages
    _reaction_messages = None


async def _reaction_message_ids() -> frozenset[int]:
    global _reaction_messages
    if _reaction_messages is None:
        ids = await models.RoleMenu.filter(style=REACTIONS, message_id__isnull=False).values_list('message_id',
                                                                                                    flat=True)
        _reaction_messages = frozenset(ids)
    return _reaction_messages


@dataclass(frozen=True)
class ReactionTarget:
    menu_id: int
    role_id: int
    single_choice: bool
    # The menu's other options, as (role_id, emoji), for single-choice menus.
    others: tuple[tuple[int, Optional[str]], ...]


async def reaction_target(guild_id: int, message_id: int, emoji: str) -> Optional[ReactionTarget]:
    """The role a reaction on a reaction menu gives, or None if it isn't one."""
    if message_id not in await _reaction_message_ids():
        return None
    menu = await models.RoleMenu.get_or_none(guild_id=guild_id, message_id=message_id, style=REACTIONS)
    if menu is None:
        return None
    key = emoji_key(emoji)
    options = await _options(menu)
    for option in options:
        if emoji_key(option.emoji) == key:
            return ReactionTarget(menu_id=menu.id, role_id=option.role_id, single_choice=menu.single_choice,
                                  others=tuple((o.role_id, o.emoji) for o in options if o.id != option.id))
    return None


async def component_menu(menu_id: int, guild_id: int) -> Optional[dict]:
    """The menu behind a button or dropdown, if it is still a buttons or dropdown menu in that server."""
    menu = await models.RoleMenu.get_or_none(id=menu_id, guild_id=guild_id)
    if menu is None or menu.style == REACTIONS:
        return None
    return view(menu, await _options(menu))


@dataclass(frozen=True)
class RoleChange:
    add: tuple[int, ...]
    remove: tuple[int, ...]


def toggle(menu: dict, option_ids: Iterable[int], member_role_ids: Iterable[int]) -> RoleChange:
    """What pressing these options does for someone holding ``member_role_ids``: each
    one they hold is removed and each one they don't is added. On a single-choice
    menu, adding one removes the menu's other roles."""
    held = set(member_role_ids)
    by_id = {o['id']: o for o in menu['options']}
    picked = [by_id[i]['role_id'] for i in dict.fromkeys(option_ids) if i in by_id]
    add = [r for r in picked if r not in held]
    remove = [r for r in picked if r in held]
    if menu['single_choice'] and add:
        add = add[-1:]
        remove = [o['role_id'] for o in menu['options'] if o['role_id'] in held and o['role_id'] not in add]
    return RoleChange(add=tuple(add), remove=tuple(dict.fromkeys(remove)))
