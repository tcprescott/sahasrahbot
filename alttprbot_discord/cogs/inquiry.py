import logging
import random
import os

import discord
from discord.commands import Option, ApplicationContext
from discord.ext import commands

from alttprbot import models
from config import Config as c


class ConfirmInquiryThread(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def on_error(self, error: Exception, item, interaction) -> None:
        raise error

    @discord.ui.button(label="Open New Inquiry", style=discord.ButtonStyle.blurple, emoji="📬", custom_id="sahasrahbot:open_inquiry")
    async def openthread(self, button: discord.ui.Button, interaction: discord.Interaction):
        inquiry_message_config = await models.InquiryMessageConfig.get(message_id=interaction.message.id)
        role = interaction.guild.get_role(inquiry_message_config.role_id)
        view = OpenInquiryThread(inquiry_message_config)

        await interaction.response.send_message(
            (
                f"This will open a private thread to {role.mention}, are you sure you want to do that?\n\n"
                "This message will stop working after one minute.\n"
                "If you did not intend to do this, simply click \"Dismiss message\" at the bottom of this response. Thanks!"
            ),
            view=view, ephemeral=True)


class OpenInquiryThread(discord.ui.View):
    def __init__(self, inquiry_message_config):
        super().__init__(timeout=60)
        self.inquiry_message_config: models.InquiryMessageConfig = inquiry_message_config

    async def on_error(self, error: Exception, item, interaction) -> None:
        raise error

    @discord.ui.button(label="Yes!", style=discord.ButtonStyle.red, row=2)
    async def yes(self, button: discord.ui.Button, interaction: discord.Interaction):
        if "PRIVATE_THREADS" not in interaction.channel.guild.features and not c.DEBUG:
            await interaction.response.send_message("Private threads must be available on this server.  Please let the server admin know so this may be fixed.", ephemeral=True)
            return

        if "SEVEN_DAY_THREAD_ARCHIVE" in interaction.channel.guild.features:
            duration = 7*24*60
        elif "THREE_DAY_THREAD_ARCHIVE" in interaction.channel.guild.features:
            duration = 3*24*60
        else:
            duration = 24*60

        msg = await interaction.channel.send("test thread") if c.DEBUG else None
        thread: discord.Thread = await interaction.channel.create_thread(name=f"Inquiry {interaction.user.name} {random.randint(0,999)}", message=msg, auto_archive_duration=duration)
        role_ping = interaction.guild.get_role(self.inquiry_message_config.role_id)

        await thread.add_user(interaction.user)
        await interaction.response.send_message(f"A new thread called {thread.mention} has been opened for this inquiry.", ephemeral=True)

        for member in role_ping.members:
            logging.info(f"Adding {member.name}#{member.discriminator} to thread {thread.name}")
            await thread.add_user(member)

        logging.info(f"Adding {interaction.user.name}#{interaction.user.discriminator} to thread {thread.name}")


class Inquiry(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.persistent_views_added = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.bot.add_view(ConfirmInquiryThread())
            self.persistent_views_added = True

    @commands.slash_command()
    async def inquiry(
        self,
        interaction: discord.Interaction,
        role: Option(discord.Role, "Role that has the members that should join the thread", required=True)
    ):
        """
        Adds a message that allows users to create a private thread to open an inquiry.
        """
        if not ctx.channel.permissions_for(ctx.author).manage_threads:
            await ctx.respond("You must have manage threads permission to use this feature.", ephemeral=True)
            return

        if "PRIVATE_THREADS" not in ctx.guild.features and not c.DEBUG:
            await ctx.respond("Private threads must be available on this server.", ephemeral=True)
            return

        if not ctx.channel.permissions_for(ctx.guild.me).create_private_threads:
            await ctx.respond("This bot needs permission to create private threads in this channel.", ephemeral=True)
            return

        if ctx.channel.permissions_for(ctx.guild.default_role).send_messages:
            await ctx.respond("`@everyone` should not be allowed to send messages in this channel.", ephemeral=True)
            return

        if not ctx.channel.permissions_for(ctx.guild.default_role).send_messages_in_threads:
            await ctx.respond("`@everyone` needs to be able to send messages in threads.", ephemeral=True)
            return

        if not ctx.channel.permissions_for(role).read_messages:
            await ctx.respond(f"{role.mention} is not allowed to see this channel.", ephemeral=True, allowed_mentions=discord.AllowedMentions(roles=False))
            return

        interaction_response = await ctx.respond(
            content=(
                "To **submit an inquiry**, click the 📬 button below, then click \"Yes!\" button in the next message to confirm.\n\n"
                f"This will open an inquiry visible to members of {role.mention}\n\n"
                "Thanks!"
            ),
            view=ConfirmInquiryThread(),
            allowed_mentions=discord.AllowedMentions(roles=False)
        )
        original_message = await interaction_response.original_message()
        await models.InquiryMessageConfig.create(message_id=original_message.id, role_id=role.id)


def check_private_threads(interaction):
    if "PRIVATE_THREADS" not in interaction.channel.guild.features:
        return False

    return True


async def setup(bot):
    await bot.add_cog(Inquiry(bot))
