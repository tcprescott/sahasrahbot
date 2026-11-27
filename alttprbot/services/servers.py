"""The Servers area of the website: the Discord servers someone administers, what's
in them (channels and roles, for the section forms) and the server's own settings.

Who administers a server: the bot owner, or a member with Administrator there. Each
section of the Servers area (settings here; role menus, voice roles, racer
verification and the server directory in their own services) checks with
``require_admin`` before it reads or changes anything.

The settings themselves live in the ``config`` table through ``guild_config``, which
records an audit entry for every change.
"""

import logging
from typing import Iterable, Optional

from alttprbot.exceptions import InvalidInputError, NotFoundError, PermissionDeniedError
from alttprbot.integrations import holyimage as holyimage_api
from alttprbot.services import discord_directory, guild_config

logger = logging.getLogger(__name__)

#: Comma-separated channel *names* the daily challenge is announced in
#: (``alttprbot_discord/notifications.py``).
DAILY_ANNOUNCER_CHANNEL = 'DailyAnnouncerChannel'
#: The game ``/holyimage`` uses when none is given (``alttprbot_discord/cogs/misc.py``).
HOLY_IMAGE_DEFAULT_GAME = 'HolyImageDefaultGame'
HOLY_IMAGE_FALLBACK_GAME = 'z3r'


async def is_admin(guild_id: int, user_id: int) -> bool:
    directory = discord_directory.get()
    return await directory.is_owner(user_id) or await directory.is_admin(guild_id, user_id)


async def require_admin(guild_id: int, user_id: int) -> None:
    """Raise unless ``user_id`` may manage ``guild_id`` (and the bot is in it)."""
    if await discord_directory.get().guild_name(guild_id) is None:
        raise NotFoundError("SahasrahBot isn't in that server.")
    if not await is_admin(guild_id, user_id):
        raise PermissionDeniedError("Only administrators of that server can manage it here.")


async def servers(admin_guild_ids: Iterable[int]) -> list[dict]:
    """The servers in ``admin_guild_ids`` (where Discord says the person has
    Administrator) that the bot is in, sorted by name."""
    return [{'id': g.id, 'name': g.name} for g in await discord_directory.get().bot_guilds(admin_guild_ids)]


async def detail(guild_id: int, user_id: int) -> dict:
    """The server's name, channels and roles, for the section forms."""
    await require_admin(guild_id, user_id)
    directory = discord_directory.get()
    return {
        'id': guild_id,
        'name': await directory.guild_name(guild_id),
        'text_channels': [{'id': c.id, 'name': c.name} for c in await directory.text_channels(guild_id)],
        'voice_channels': [{'id': c.id, 'name': c.name} for c in await directory.voice_channels(guild_id)],
        'roles': [{'id': r.id, 'name': r.name, 'position': r.position, 'assignable': r.assignable}
                  for r in await directory.role_details(guild_id)],
    }


# --- settings ----------------------------------------------------------------


async def holy_image_games() -> list[str]:
    """The games holy images exist for, or an empty list when the site can't be reached."""
    try:
        return sorted(await holyimage_api.get_holy_images())
    except Exception:
        logger.warning("Couldn't load the holy image games.", exc_info=True)
        return []


def _split(value: Optional[str]) -> list[str]:
    return [name.strip() for name in (value or '').split(',') if name.strip()]


async def settings(guild_id: int, user_id: int) -> dict:
    """The server's settings, with each daily channel marked as usable or not."""
    await require_admin(guild_id, user_id)
    usable = {c.name.lstrip('#') for c in await discord_directory.get().text_channels(guild_id)}
    daily = _split(await guild_config.get(guild_id, DAILY_ANNOUNCER_CHANNEL))
    return {
        'daily_channels': [{'name': name, 'usable': name in usable} for name in daily],
        'holy_image_game': await guild_config.get(guild_id, HOLY_IMAGE_DEFAULT_GAME),
        'holy_image_fallback': HOLY_IMAGE_FALLBACK_GAME,
        'holy_image_games': await holy_image_games(),
    }


async def _checked_daily_channels(guild_id: int, daily_channels: list[str], current: list[str]) -> list[str]:
    """The daily channel names to save, without ``#`` or repeats. A channel that's
    already set may stay even if the bot can't post there now; a new one has to be
    somewhere it can."""
    names = list(dict.fromkeys(name.strip().lstrip('#') for name in daily_channels if name.strip().lstrip('#')))
    if any(',' in name for name in names):
        raise InvalidInputError("Channel names can't contain commas.")
    usable = {c.name.lstrip('#') for c in await discord_directory.get().text_channels(guild_id)}
    unknown = [name for name in names if name not in usable and name not in current]
    if unknown:
        raise InvalidInputError(f"SahasrahBot can't post in #{unknown[0]}. Pick a channel from the list.")
    return names


async def _checked_holy_image_game(holy_image_game: Optional[str]) -> Optional[str]:
    """The game to save, or None for the default. Any game is taken while the holy
    image site can't be reached to check it."""
    game = (holy_image_game or '').strip()
    if not game:
        return None
    games = await holy_image_games()
    if games and game not in games:
        raise InvalidInputError(f"There are no holy images for “{game}”.")
    return game


async def _save(guild_id: int, parameter: str, value: Optional[str]) -> None:
    """Store ``value``, or remove the setting for None; nothing when it's unchanged."""
    if value == await guild_config.get(guild_id, parameter):
        return
    if value is None:
        await guild_config.delete_value(guild_id, parameter)
    else:
        await guild_config.set_value(guild_id, parameter, value)


async def update_settings(guild_id: int, user_id: int, daily_channels: list[str],
                          holy_image_game: Optional[str]) -> dict:
    """Replace the server's settings. ``daily_channels`` are channel names (with or
    without ``#``); an empty list turns the daily announcement off. A ``None`` or empty
    ``holy_image_game`` goes back to the default. Nothing is saved unless both are valid."""
    await require_admin(guild_id, user_id)
    current = _split(await guild_config.get(guild_id, DAILY_ANNOUNCER_CHANNEL))
    names = await _checked_daily_channels(guild_id, daily_channels, current)
    game = await _checked_holy_image_game(holy_image_game)

    if names != current:
        await _save(guild_id, DAILY_ANNOUNCER_CHANNEL, ','.join(names) or None)
    await _save(guild_id, HOLY_IMAGE_DEFAULT_GAME, game)
    return await settings(guild_id, user_id)
