"""Elections on Discord: the post that shows an election, and the lookups the
election service needs (``alttprbot.services.discord_directory``).

The website creates and manages elections. Discord shows each one as an embed with
Vote and Manage links and an End election button, and swaps it for the winners and
a link to the full count when it closes.
"""

import asyncio
import logging
from typing import Optional

import discord
from discord.ext import commands

import config
from alttprbot.exceptions import InvalidInputError, NotFoundError, PermissionDeniedError
from alttprbot.services import discord_directory, elections
from alttprbot.services.discord_directory import Named, RoleInfo
from alttprbot_discord.audit import audited
from alttprbot.util import discord_members

logger = logging.getLogger(__name__)

END_BUTTON_ID = "sahasrahbot:rankedchoice:end_election"  # unchanged, so buttons on old posts keep working
OPEN_COLOUR = discord.Colour(0x6D3FC0)
CLOSED_COLOUR = discord.Colour.green()

POSTABLE_CHANNEL_TYPES = (discord.ChannelType.text, discord.ChannelType.news)
VOICE_CHANNEL_TYPES = (discord.ChannelType.voice, discord.ChannelType.stage_voice)


def vote_url(election_id: int) -> str:
    return f"{config.APP_URL}/ranked_choice/{election_id}"


def manage_url(election_id: int) -> str:
    return f"{config.APP_URL}/elections/{election_id}/edit"


def results_url(election_id: int) -> str:
    return f"{config.APP_URL}/elections/{election_id}/results"


def _when(dt) -> str:
    return f"{discord.utils.format_dt(dt, 'f')} ({discord.utils.format_dt(dt, 'R')})"


def build_embed(view: dict) -> discord.Embed:
    """The election's embed, from ``elections.post_view``."""
    closed = view['status'] == elections.CLOSED
    title = f"✅ {view['title']} (closed)" if closed else f"🗳️ {view['title']}"
    embed = discord.Embed(title=title[:256], description=view['description'],
                          colour=CLOSED_COLOUR if closed else OPEN_COLOUR)
    if closed:
        winners = view['winners']
        embed.add_field(name="Winners" if len(winners) != 1 else "Winner",
                        value=" · ".join(f"{i}. {w}" for i, w in enumerate(winners, start=1)) or "No ballots were cast.",
                        inline=False)
        embed.add_field(name="Method", value=view['method_label'])
        embed.add_field(name="Ballots", value=str(view['ballots']))
        if view['closed_at']:
            embed.add_field(name="Closed", value=discord.utils.format_dt(view['closed_at'], 'f'))
        embed.set_footer(text=f"Election #{view['id']}")
        return embed

    embed.add_field(name="Method", value=view['method_label'])
    if view['method'] == 'stv':
        embed.add_field(name="Winners", value=str(view['seats']))
    if view['show_vote_count']:
        embed.add_field(name="Ballots", value=str(view['ballots']))
    embed.add_field(name="Who can vote",
                    value=f"<@&{view['voter_role_id']}>" if view['voter_role_id'] else "Everyone in the server")
    embed.add_field(name="Closes", value=_when(view['closes_at']) if view['closes_at'] else "When an admin ends it")
    embed.add_field(name="Run by", value=f"<@{view['owner_id']}>")
    embed.set_footer(text=f"Results are shown when voting closes. · Election #{view['id']}")
    return embed


class ElectionView(discord.ui.View):
    """The buttons under an open election. Registered once at startup as a
    persistent view, so End election works on every post, old ones included."""

    def __init__(self, election_id: Optional[int] = None):
        super().__init__(timeout=None)
        if election_id is not None:
            self.add_item(discord.ui.Button(label="Vote", url=vote_url(election_id)))
            self.add_item(discord.ui.Button(label="Manage", url=manage_url(election_id)))
        # The End button goes last, after the links.
        self.remove_item(self.end_election)
        self.add_item(self.end_election)

    @discord.ui.button(label="End election", custom_id=END_BUTTON_ID, style=discord.ButtonStyle.danger)
    @audited('End election button')
    async def end_election(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            await elections.close_from_message(interaction.message.id, interaction.user.id)
        except (PermissionDeniedError, InvalidInputError, NotFoundError) as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return
        # The ElectionClosed event refreshes the post.
        await interaction.followup.send("Election ended. The results are posted.", ephemeral=True)


def _closed_view(election_id: int) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="See the full count", url=results_url(election_id)))
    return view


def message_parts(view: dict) -> dict:
    """The embed and buttons for an election's post."""
    if view['status'] == elections.CLOSED:
        return {'embed': build_embed(view), 'view': _closed_view(view['id'])}
    return {'embed': build_embed(view), 'view': ElectionView(view['id'])}


async def _channel(bot: discord.Client, channel_id: int):
    channel = bot.get_channel(channel_id)
    if channel is None:
        channel = await bot.fetch_channel(channel_id)
    return channel


async def post(bot: discord.Client, election_id: int) -> int:
    view = await elections.post_view(election_id)
    try:
        channel = await _channel(bot, view['channel_id'])
        message = await channel.send(**message_parts(view))
    except discord.Forbidden as e:
        raise InvalidInputError("SahasrahBot isn't allowed to post in that channel.") from e
    except discord.HTTPException as e:
        logger.exception("Couldn't post election %s", election_id)
        raise InvalidInputError("Discord didn't accept the post. Try again in a minute.") from e
    return message.id


async def refresh(bot: discord.Client, election_id: int) -> None:
    """Redraw an election's post. Best effort: a deleted post is left alone."""
    view = await elections.post_view(election_id)
    if view is None or not view['message_id'] or not view['channel_id']:
        return
    try:
        channel = await _channel(bot, view['channel_id'])
        message = channel.get_partial_message(view['message_id'])
        await message.edit(attachments=[], **message_parts(view))
    except discord.NotFound:
        logger.info("Election %s's post is gone; not refreshing it", election_id)


async def delete_post(bot: discord.Client, channel_id: Optional[int], message_id: Optional[int]) -> None:
    if not channel_id or not message_id:
        return
    try:
        channel = await _channel(bot, channel_id)
        await channel.get_partial_message(message_id).delete()
    except discord.NotFound:
        pass


class DiscordDirectory:
    """``discord_directory.Directory`` backed by the bot. Needs no privileged intents."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def is_owner(self, user_id: int) -> bool:
        return await self.bot.is_owner(discord.Object(id=user_id))

    async def _guild(self, guild_id: int) -> Optional[discord.Guild]:
        guild = self.bot.get_guild(guild_id)
        if guild is not None:
            return guild
        try:
            return await self.bot.fetch_guild(guild_id)
        except discord.HTTPException:
            return None

    async def _member(self, guild_id: int, user_id: int) -> Optional[discord.Member]:
        guild = await self._guild(guild_id)
        if guild is None:
            return None
        return await discord_members.get_member(guild, user_id)

    async def member_role_ids(self, guild_id: int, user_id: int) -> Optional[list[int]]:
        member = await self._member(guild_id, user_id)
        return None if member is None else [r.id for r in member.roles]

    async def is_admin(self, guild_id: int, user_id: int) -> bool:
        # One member lookup in this one server (the cache, else one REST call).
        member = await self._member(guild_id, user_id)
        return member is not None and member.guild_permissions.administrator

    async def admin_guilds(self, user_id: int) -> list[Named]:
        limit = asyncio.Semaphore(8)

        async def check(guild):
            async with limit:
                return guild if await self.is_admin(guild.id, user_id) else None

        found = await asyncio.gather(*(check(g) for g in self.bot.guilds))
        return sorted((Named(g.id, g.name) for g in found if g is not None), key=lambda g: g.name.casefold())

    async def bot_guilds(self, guild_ids) -> list[Named]:
        guilds = (self.bot.get_guild(int(gid)) for gid in set(guild_ids))
        return sorted((Named(g.id, g.name) for g in guilds if g is not None), key=lambda g: g.name.casefold())

    async def guild_name(self, guild_id: int) -> Optional[str]:
        guild = await self._guild(guild_id)
        return guild.name if guild else None

    async def text_channels(self, guild_id: int) -> list[Named]:
        # The gateway cache, not guild.fetch_channels(): the guilds intent keeps it
        # complete, and it skips channel types discord.py doesn't know, which
        # fetch_channels() raises InvalidData on (a server with one couldn't be picked).
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return []
        me = guild.me
        channels = [c for c in guild.channels if getattr(c, 'type', None) in POSTABLE_CHANNEL_TYPES]
        if me is not None:
            channels = [c for c in channels
                        if c.permissions_for(me).send_messages and c.permissions_for(me).embed_links]
        return [Named(c.id, f"#{c.name}") for c in sorted(channels, key=lambda c: c.position)]

    async def roles(self, guild_id: int) -> list[Named]:
        guild = await self._guild(guild_id)
        if guild is None:
            return []
        roles = await guild.fetch_roles()
        return [Named(r.id, f"@{r.name}") for r in sorted(roles, key=lambda r: -r.position)
                if not r.is_default() and not r.managed]

    async def role_details(self, guild_id: int) -> list[RoleInfo]:
        guild = await self._guild(guild_id)
        if guild is None:
            return []
        me = guild.me
        can_manage = me is None or me.guild_permissions.manage_roles
        top = None if me is None else me.top_role.position
        roles = await guild.fetch_roles()
        return [RoleInfo(r.id, f"@{r.name}", r.position, can_manage and (top is None or r.position < top))
                for r in sorted(roles, key=lambda r: -r.position) if not r.is_default() and not r.managed]

    async def voice_channels(self, guild_id: int) -> list[Named]:  # NOSONAR
        # The gateway cache, like text_channels.
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return []
        channels = [c for c in guild.channels if getattr(c, 'type', None) in VOICE_CHANNEL_TYPES]
        return [Named(c.id, c.name) for c in sorted(channels, key=lambda c: c.position)]

    async def post_election(self, election_id: int) -> int:
        return await post(self.bot, election_id)


def register(bot: commands.Bot) -> None:
    discord_directory.register(DiscordDirectory(bot))
