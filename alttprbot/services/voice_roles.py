"""Voice roles: members in a mapped voice channel get the mapped role while they are in it.

The ``voice_role`` table. Callers pass ids, never Discord objects. Managed by server
administrators (and the bot owner) on the website's server page, ``/api/v1`` and MCP;
the Discord side is ``alttprbot_discord/cogs/voicerole.py``.
"""

from typing import List, Optional

from alttprbot import models
from alttprbot.exceptions import InvalidInputError, NotFoundError
from alttprbot.services import audit, discord_directory, servers

CHANNEL_GONE = "This voice channel no longer exists."
ROLE_GONE = "This role no longer exists."
ROLE_UNASSIGNABLE = ("SahasrahBot can't give this role: it's above SahasrahBot's own role, "
                     "or SahasrahBot doesn't have Manage Roles.")


async def for_guild(guild_id: int) -> List[models.VoiceRole]:
    return await models.VoiceRole.filter(guild_id=guild_id)


async def create(guild_id: int, voice_channel_id: int, role_id: int,
                 target: Optional[str] = None) -> models.VoiceRole:
    voice_role = await models.VoiceRole.create(guild_id=guild_id, voice_channel_id=voice_channel_id, role_id=role_id)
    await audit.record(audit.VOICE_ROLE_CREATED, target=target or f'Voice channel {voice_channel_id}',
                       guild_id=guild_id,
                       details={'voice_role_id': voice_role.id, 'voice_channel_id': voice_channel_id,
                                'role_id': role_id})
    return voice_role


async def delete(guild_id: int, voice_role_id: int, target: Optional[str] = None) -> bool:
    deleted = await models.VoiceRole.filter(guild_id=guild_id, id=voice_role_id).delete()
    if deleted:
        await audit.record(audit.VOICE_ROLE_DELETED, target=target or f'Voice role {voice_role_id}',
                           guild_id=guild_id, details={'voice_role_id': voice_role_id})
    return bool(deleted)


# --- managing them (web, API, MCP) ----------------------------------------------


def _target(channel: Optional[str], role: Optional[str]) -> str:
    return f"{channel or 'Deleted voice channel'} → {role or 'deleted role'}"


async def overview(guild_id: int, user_id: int) -> dict:
    """The server's voice roles, with names and anything that stops one working, plus the
    voice channels and roles the add form offers (``assignable``: the bot can give it)."""
    await servers.require_admin(guild_id, user_id)
    directory = discord_directory.get()
    channels = await directory.voice_channels(guild_id)
    roles = await directory.role_details(guild_id)
    assignable = {r.id for r in roles if r.assignable}
    channel_names = {c.id: c.name for c in channels}
    channel_order = {c.id: i for i, c in enumerate(channels)}
    role_names = {r.id: r.name for r in roles}

    mappings = []
    for vr in await for_guild(guild_id):
        if vr.voice_channel_id not in channel_names:
            problem = CHANNEL_GONE
        elif vr.role_id not in role_names:
            problem = ROLE_GONE
        elif vr.role_id not in assignable:
            problem = ROLE_UNASSIGNABLE
        else:
            problem = None
        mappings.append({
            'id': vr.id,
            'voice_channel_id': vr.voice_channel_id,
            'voice_channel_name': channel_names.get(vr.voice_channel_id),
            'role_id': vr.role_id,
            'role_name': role_names.get(vr.role_id),
            'problem': problem,
        })
    mappings.sort(key=lambda m: (channel_order.get(m['voice_channel_id'], len(channels)),
                                 (m['role_name'] or '').casefold(), m['id']))
    return {
        'voice_roles': mappings,
        'voice_channels': [{'id': c.id, 'name': c.name} for c in channels],
        'roles': [{'id': r.id, 'name': r.name, 'assignable': r.id in assignable} for r in roles],
    }


async def add(guild_id: int, user_id: int, voice_channel_id: int, role_id: int) -> dict:
    """Give ``role_id`` to everyone in ``voice_channel_id`` while they're in it."""
    await servers.require_admin(guild_id, user_id)
    directory = discord_directory.get()
    channel = next((c for c in await directory.voice_channels(guild_id) if c.id == voice_channel_id), None)
    if channel is None:
        raise InvalidInputError("Pick a voice channel in this server.")
    role = next((r for r in await directory.role_details(guild_id) if r.id == role_id), None)
    if role is None:
        raise InvalidInputError("Pick a role in this server.")
    if not role.assignable:
        raise InvalidInputError(f"SahasrahBot can't give {role.name}. Move SahasrahBot's role above it in "
                                "Discord's server settings, and check it has Manage Roles.")
    if await models.VoiceRole.exists(guild_id=guild_id, voice_channel_id=voice_channel_id, role_id=role_id):
        raise InvalidInputError(f"{channel.name} already gives {role.name}.")
    voice_role = await create(guild_id, voice_channel_id, role_id, target=_target(channel.name, role.name))
    return {'id': voice_role.id, 'voice_channel_id': voice_channel_id, 'voice_channel_name': channel.name,
            'role_id': role_id, 'role_name': role.name, 'problem': None}


async def remove(guild_id: int, user_id: int, voice_role_id: int) -> None:
    """Stop giving a voice role. People who have it keep it until they next leave the channel."""
    await servers.require_admin(guild_id, user_id)
    voice_role = await models.VoiceRole.get_or_none(guild_id=guild_id, id=voice_role_id)
    if voice_role is None:
        raise NotFoundError("That voice role doesn't exist.")
    directory = discord_directory.get()
    channel = next((c.name for c in await directory.voice_channels(guild_id) if c.id == voice_role.voice_channel_id),
                   None)
    role = next((r.name for r in await directory.roles(guild_id) if r.id == voice_role.role_id), None)
    await delete(guild_id, voice_role_id, target=_target(channel, role))
