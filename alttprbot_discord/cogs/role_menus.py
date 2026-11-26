"""Role menus are made and edited on the website (``/role-menus``). This cog answers
reactions on reaction menus, keeps menu buttons and dropdowns working across
restarts, and gives admins ``/rolemenus``, which lists the server's menus with links."""

from urllib.parse import urlencode

import discord
from discord import app_commands
from discord.ext import commands

import config
from alttprbot.services import role_menus
from alttprbot_discord.role_menus import RoleMenuButton, RoleMenuSelect, reaction_changed


def list_url(guild_id: int) -> str:
    """The server's role menus on the website (the Role menus section of its server page)."""
    return f"{config.APP_URL}/servers/{guild_id}/role-menus"


def edit_url(guild_id: int, menu_id: int) -> str:
    return f"{list_url(guild_id)}/{menu_id}"


def new_url(guild_id: int, channel_id: int) -> str:
    return f"{list_url(guild_id)}/new?{urlencode({'channel': channel_id})}"


def menu_line(menu: dict, guild_id: int) -> str:
    emoji = " ".join(o['emoji'] for o in menu['options'] if o['emoji'])
    where = (f"https://discord.com/channels/{guild_id}/{menu['channel_id']}/{menu['message_id']}"
             if menu['message_id'] else f"<#{menu['channel_id']}>")
    style = role_menus.STYLE_LABELS.get(menu['style'], menu['style'])
    return f"[{menu['title']}]({edit_url(guild_id, menu['id'])}) · {style} · {where} {emoji}".strip()


class RoleMenus(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_dynamic_items(RoleMenuButton, RoleMenuSelect)

    async def cog_unload(self):
        self.bot.remove_dynamic_items(RoleMenuButton, RoleMenuSelect)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await reaction_changed(self.bot, payload, added=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await reaction_changed(self.bot, payload, added=False)

    @app_commands.command(name="rolemenus", description="List this server's role menus, with links to edit them on the website.")
    @app_commands.guild_only()
    # Hidden from everyone without Administrator; server owners can change that in Integrations.
    @app_commands.default_permissions(administrator=True)
    async def rolemenus(self, interaction: discord.Interaction):
        channel = interaction.channel
        channel_id = getattr(channel, "parent_id", None) or channel.id
        menus = await role_menus.menus_in_guild(interaction.guild.id)
        if menus:
            text = "\n".join(menu_line(m, interaction.guild.id) for m in menus)[:1900]
        else:
            text = "This server has no role menus yet."
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="New role menu", url=new_url(interaction.guild.id, channel_id)))
        view.add_item(discord.ui.Button(label="All role menus", url=list_url(interaction.guild.id)))
        await interaction.response.send_message(text, view=view, ephemeral=True, suppress_embeds=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(RoleMenus(bot))
