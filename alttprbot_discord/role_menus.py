"""Role menus on Discord: drawing a menu's message, the buttons and dropdown people
use, and the gateway ``alttprbot/services/role_menus.py`` posts through.

Buttons and dropdowns are dynamic items (custom ids ``rolemenu:<menu>:<option>`` and
``rolemenu:<menu>:pick``), so they keep working across restarts without a view per
menu. Reactions are handled by the cog (``cogs/role_menus.py``).

Everything works without privileged intents: a button press carries the member and
their roles, and a reaction is answered with a direct role add or remove.
"""

import logging
import re
from typing import Optional

import discord
from discord.ext import commands

from alttprbot.exceptions import InvalidInputError
from alttprbot.services import role_menus
from alttprbot.services.discord_directory import Named
from alttprbot.services.role_menus import BUTTONS, DROPDOWN, REACTIONS, RoleChange, ServerDetails, ServerRole

logger = logging.getLogger(__name__)

COLOUR = discord.Colour(0x6D3FC0)
POSTABLE_CHANNEL_TYPES = (discord.ChannelType.text, discord.ChannelType.news)
UNKNOWN_EMOJI = 10014
ADDED_REASON = "Picked from a role menu"
REMOVED_REASON = "Removed from a role menu"


# --- the message -----------------------------------------------------------------------


def build_embed(menu: dict) -> discord.Embed:
    embed = discord.Embed(title=menu['title'][:256], description=menu['description'], colour=COLOUR)
    if menu['style'] == REACTIONS:
        lines = []
        for option in menu['options']:
            line = f"{option['emoji'] or ''} **{option['label']}**".strip()
            if option['description']:
                line += f" – {option['description']}"
            lines.append(line)
        if lines:
            embed.add_field(name="React to pick a role" if not menu['single_choice'] else "React to pick one role",
                            value="\n".join(lines)[:1024], inline=False)
    elif menu['single_choice']:
        embed.set_footer(text="You can have one of these roles at a time.")
    return embed


def _emoji(text: Optional[str]):
    return discord.PartialEmoji.from_str(text) if text else None


class RoleMenuButton(discord.ui.DynamicItem[discord.ui.Button], template=r'rolemenu:(?P<menu>\d+):(?P<option>\d+)'):
    def __init__(self, menu_id: int, option: Optional[dict] = None, option_id: Optional[int] = None):
        option_id = option['id'] if option else option_id
        super().__init__(discord.ui.Button(
            label=option['label'] if option else None,
            emoji=_emoji(option['emoji']) if option else None,
            style=discord.ButtonStyle.secondary,
            custom_id=f"rolemenu:{menu_id}:{option_id}",
        ))
        self.menu_id = menu_id
        self.option_id = option_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str], /):
        return cls(int(match['menu']), option_id=int(match['option']))

    async def callback(self, interaction: discord.Interaction):
        await pick(interaction, self.menu_id, [self.option_id], redraw=False)


class RoleMenuSelect(discord.ui.DynamicItem[discord.ui.Select], template=r'rolemenu:(?P<menu>\d+):pick'):
    def __init__(self, menu_id: int, menu: Optional[dict] = None):
        options = [discord.SelectOption(label=o['label'], value=str(o['id']), emoji=_emoji(o['emoji']),
                                        description=(o['description'] or None) and o['description'][:100])
                   for o in (menu['options'] if menu else [])]
        single = bool(menu and menu['single_choice'])
        super().__init__(discord.ui.Select(
            custom_id=f"rolemenu:{menu_id}:pick",
            placeholder="Pick a role to add or remove" if single or not menu else "Pick roles to add or remove",
            min_values=1,
            max_values=1 if single else max(1, len(options)),
            options=options or [discord.SelectOption(label="…")],
        ))
        self.menu_id = menu_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Select, match: re.Match[str], /):
        return cls(int(match['menu']))

    async def callback(self, interaction: discord.Interaction):
        await pick(interaction, self.menu_id, [int(v) for v in self.item.values], redraw=True)


def build_view(menu: dict) -> Optional[discord.ui.View]:
    if menu['style'] == BUTTONS:
        view = discord.ui.View(timeout=None)
        for option in menu['options']:
            view.add_item(RoleMenuButton(menu['id'], option))
        return view
    if menu['style'] == DROPDOWN:
        view = discord.ui.View(timeout=None)
        view.add_item(RoleMenuSelect(menu['id'], menu))
        return view
    return None


def message_parts(menu: dict) -> dict:
    view = build_view(menu)
    return {'content': None, 'embed': build_embed(menu), 'view': view if view is not None else discord.ui.View()}


# --- people picking ------------------------------------------------------------------------


def _describe(change: RoleChange) -> str:
    parts = []
    if change.add:
        parts.append("Added " + ", ".join(f"<@&{r}>" for r in change.add) + ".")
    if change.remove:
        parts.append("Removed " + ", ".join(f"<@&{r}>" for r in change.remove) + ".")
    return " ".join(parts) or "Nothing changed."


async def pick(interaction: discord.Interaction, menu_id: int, option_ids: list[int], *, redraw: bool) -> None:
    """Someone pressed a button or picked from the dropdown: add or remove the roles
    and tell them privately what changed."""
    menu = await role_menus.component_menu(menu_id, interaction.guild_id) if interaction.guild_id else None
    if redraw and menu is not None:
        # Redrawing the dropdown clears the pick, so the next one starts fresh.
        await interaction.response.edit_message(view=build_view(menu))
    else:
        await interaction.response.defer(ephemeral=True, thinking=True)
    if menu is None:
        await interaction.followup.send("This role menu isn't in use any more.", ephemeral=True)
        return
    member = interaction.user
    if getattr(member, 'roles', None) is None:  # not a server member: a DM can't reach here, but be sure
        await interaction.followup.send("Use this menu in its server.", ephemeral=True)
        return
    change = role_menus.toggle(menu, option_ids, [r.id for r in member.roles])
    guild = interaction.guild
    try:
        if change.remove:
            await member.remove_roles(*(discord.Object(id=r) for r in change.remove), reason=REMOVED_REASON)
        if change.add:
            await member.add_roles(*(discord.Object(id=r) for r in change.add), reason=ADDED_REASON)
    except discord.Forbidden:
        logger.warning("Role menu %s in guild %s: missing permission to change roles", menu_id, guild.id)
        await interaction.followup.send(
            "SahasrahBot isn't allowed to change that role. Please tell a server admin: SahasrahBot needs "
            "Manage Roles and a role above the ones on this menu.", ephemeral=True)
        return
    await interaction.followup.send(_describe(change), ephemeral=True, allowed_mentions=discord.AllowedMentions.none())


async def reaction_changed(bot: commands.Bot, payload: discord.RawReactionActionEvent, added: bool) -> None:
    """A reaction was added to or removed from a message: if it's a reaction menu, add
    or remove the role. Needs no member lookup."""
    if payload.guild_id is None or (bot.user and payload.user_id == bot.user.id):
        return
    if payload.member is not None and payload.member.bot:
        return
    target = await role_menus.reaction_target(payload.guild_id, payload.message_id, str(payload.emoji))
    if target is None:
        return
    http = bot.http
    try:
        if added:
            await http.add_role(payload.guild_id, payload.user_id, target.role_id, reason=ADDED_REASON)
            if target.single_choice:
                await _clear_other_picks(bot, payload, target)
        else:
            await http.remove_role(payload.guild_id, payload.user_id, target.role_id, reason=REMOVED_REASON)
    except discord.Forbidden:
        logger.warning("Role menu %s in guild %s: missing permission to change role %s",
                       target.menu_id, payload.guild_id, target.role_id)
    except discord.NotFound:
        logger.info("Role menu %s: role %s or member %s is gone", target.menu_id, target.role_id, payload.user_id)


async def _clear_other_picks(bot: commands.Bot, payload: discord.RawReactionActionEvent, target) -> None:
    """Single-choice reaction menu: drop the person's other roles and reactions on it."""
    for role_id, emoji in target.others:
        await bot.http.remove_role(payload.guild_id, payload.user_id, role_id, reason=REMOVED_REASON)
        if emoji:
            try:
                channel = bot.get_partial_messageable(payload.channel_id, guild_id=payload.guild_id)
                await channel.get_partial_message(payload.message_id).remove_reaction(
                    discord.PartialEmoji.from_str(emoji), discord.Object(id=payload.user_id))
            except discord.HTTPException:
                pass  # needs Manage Messages; the role is gone either way


# --- the gateway the service posts through ---------------------------------------------------


class RoleMenuGateway:
    """``role_menus.RoleMenuDiscord`` backed by the bot."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def server(self, guild_id: int) -> Optional[ServerDetails]:
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return None
        me = guild.me
        channels = [c for c in guild.channels if getattr(c, 'type', None) in POSTABLE_CHANNEL_TYPES]
        if me is not None:
            channels = [c for c in channels if _can_post(c.permissions_for(me))]
        roles = [ServerRole(r.id, f"@{r.name}", _can_give(me, r))
                 for r in sorted(guild.roles, key=lambda r: -r.position) if not r.is_default() and not r.managed]
        return ServerDetails(
            channels=[Named(c.id, f"#{c.name}") for c in sorted(channels, key=lambda c: c.position)],
            roles=roles,
            emojis=[Named(e.id, str(e)) for e in sorted(guild.emojis, key=lambda e: e.name.casefold())
                    if e.available],
        )

    async def _channel(self, channel_id: int):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            channel = await self.bot.fetch_channel(channel_id)
        return channel

    async def publish(self, menu: dict) -> int:
        try:
            channel = await self._channel(menu['channel_id'])
            if menu['posted_by_bot']:
                message = await self._post_or_edit(channel, menu)
            else:
                message = await channel.fetch_message(menu['message_id'])
            await self._sync_reactions(channel, message, menu)
        except discord.NotFound as e:
            raise InvalidInputError("The message this menu is on was deleted. Repost the menu to put it back.") from e
        except discord.Forbidden as e:
            raise InvalidInputError("SahasrahBot isn't allowed to post this menu there. It needs View Channel, "
                                    "Send Messages, Embed Links, Read Message History and Add Reactions.") from e
        except discord.HTTPException as e:
            logger.warning("Discord refused role menu %s: %s", menu['id'], e)
            raise InvalidInputError(f"Discord didn't accept the menu: {e.text or e}") from e
        return message.id

    async def _post_or_edit(self, channel, menu: dict) -> discord.Message:
        parts = message_parts(menu)
        if menu['message_id']:
            try:
                return await channel.get_partial_message(menu['message_id']).edit(**parts)
            except discord.NotFound:
                logger.info("Role menu %s's message is gone; posting a new one", menu['id'])
        return await channel.send(**parts)

    async def _sync_reactions(self, channel, message: discord.Message, menu: dict) -> None:
        wanted = [o['emoji'] for o in menu['options'] if o['emoji']] if menu['style'] == REACTIONS else []
        wanted_keys = {role_menus.emoji_key(e) for e in wanted}
        if not getattr(message, 'reactions', None):
            message = await channel.fetch_message(message.id)
        reactions = getattr(message, 'reactions', None) or []
        for reaction in reactions:
            if reaction.me and role_menus.emoji_key(str(reaction.emoji)) not in wanted_keys:
                await message.remove_reaction(reaction.emoji, self.bot.user)
        have = {role_menus.emoji_key(str(r.emoji)) for r in reactions if r.me}
        for emoji in wanted:
            if role_menus.emoji_key(emoji) in have:
                continue
            try:
                await message.add_reaction(discord.PartialEmoji.from_str(emoji))
            except discord.HTTPException as e:
                if e.code == UNKNOWN_EMOJI or e.status == 400:
                    raise InvalidInputError(f"SahasrahBot can't use the emoji {emoji}. Custom emoji have to come "
                                            "from a server SahasrahBot is in.") from e
                raise

    async def remove(self, menu: dict) -> None:
        if not menu['message_id']:
            return
        try:
            channel = await self._channel(menu['channel_id'])
            message = channel.get_partial_message(menu['message_id'])
            if menu['posted_by_bot']:
                await message.delete()
            else:
                for option in menu['options']:
                    if option['emoji']:
                        await message.remove_reaction(discord.PartialEmoji.from_str(option['emoji']), self.bot.user)
        except discord.HTTPException as e:
            logger.info("Couldn't take role menu %s off Discord: %s", menu['id'], e)


def _can_give(me: Optional[discord.Member], role) -> bool:
    """Whether the bot can give ``role``: it has Manage Roles and a higher role.
    Without the bot's member (not cached yet) it can't tell, so it says yes."""
    if me is None:
        return True
    return bool(me.guild_permissions.manage_roles and role < me.top_role)


def _can_post(perms: discord.Permissions) -> bool:
    return perms.view_channel and perms.send_messages and perms.embed_links and perms.add_reactions


def register(bot: commands.Bot) -> None:
    role_menus.register(RoleMenuGateway(bot))
