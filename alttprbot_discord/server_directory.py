"""The server directory on Discord: checking invites and posting the list.

``register(bot)`` hands both to ``alttprbot.services.discord_servers`` at startup;
the website's "Post to Discord" and ``/discordservers refresh`` post through it.
"""

import discord

from alttprbot.exceptions import InvalidInputError
from alttprbot.services import discord_servers
from alttprbot.services.discord_servers import InviteInfo, ServerListLayout


async def lookup_invite(bot: discord.Client, code: str) -> InviteInfo:
    try:
        invite = await bot.fetch_invite(code, with_counts=True, with_expiration=True)
    except discord.NotFound:
        raise InvalidInputError("That invite doesn't work: it may have expired or been deleted.")
    except discord.HTTPException:
        raise InvalidInputError("Discord couldn't check that invite just now. Try again in a minute.")
    guild = getattr(invite, 'guild', None)
    if guild is None:
        raise InvalidInputError("That invite isn't for a server.")
    return InviteInfo(code=invite.code, server_name=guild.name,
                      member_count=getattr(invite, 'approximate_member_count', None),
                      expires_at=getattr(invite, 'expires_at', None))


async def post_layout(guild, bot_user, layout: ServerListLayout) -> None:
    """Delete ``bot_user``'s messages in each of the layout's channels, then post its pages."""
    def is_me(m):
        return m.author == bot_user

    channels = {}
    for channel_id in layout.channel_ids:
        channel = guild.get_channel(channel_id)
        if channel is None:
            raise InvalidInputError(f"SahasrahBot can't see the channel <#{channel_id}> any more. "
                                    "Pick another channel for the categories posted there.")
        channels[channel_id] = channel

    current = None
    try:
        for channel in channels.values():
            current = channel
            await channel.purge(limit=100, check=is_me)
        for page in layout.pages:
            current = channels[page.channel_id]
            await current.send(discord_servers.page_text(page))
    except discord.Forbidden:
        raise InvalidInputError(f"SahasrahBot needs View Channel, Send Messages, Read Message History and "
                                f"Manage Messages in #{current.name}.")


def register(bot: discord.Client) -> None:
    async def lookup(code: str) -> InviteInfo:
        return await lookup_invite(bot, code)

    async def poster(guild_id: int, layout: ServerListLayout) -> None:
        guild = bot.get_guild(guild_id)
        if guild is None:
            raise InvalidInputError("SahasrahBot isn't in that server any more.")
        await post_layout(guild, bot.user, layout)

    discord_servers.register(lookup, poster)
