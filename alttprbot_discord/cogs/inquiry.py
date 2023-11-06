import logging
import random

import discord
from discord import app_commands
from discord.ext import commands

import config
from alttprbot import models


# TODO: make work with discord.py 2.0


class ConfirmInquiryThread(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # async def on_error(self, error: Exception, item, interaction) -> None:
    #     raise error

    @discord.ui.button(label="Open New Inquiry", style=discord.ButtonStyle.blurple, emoji="📬", custom_id="sahasrahbot:open_inquiry")
    async def openthread(self, interaction: discord.Interaction, button: discord.ui.Button):
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

    @discord.ui.button(label="Yes!", style=discord.ButtonStyle.red, row=2)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if "PRIVATE_THREADS" not in interaction.channel.guild.features and not config.DEBUG:
            await interaction.response.send_message("Private threads must be available on this server.  Please let the server admin know so this may be fixed.", ephemeral=True)
            return

        if "SEVEN_DAY_THREAD_ARCHIVE" in interaction.channel.guild.features:
            duration = 7*24*60
        elif "THREE_DAY_THREAD_ARCHIVE" in interaction.channel.guild.features:
            duration = 3*24*60
        else:
            duration = 24*60

        msg = await interaction.channel.send("test thread") if config.DEBUG else None
        thread: discord.Thread = await interaction.channel.create_thread(name=f"Inquiry {interaction.user.name} {random.randint(0,999)}", message=msg, auto_archive_duration=duration)
        role_ping = interaction.guild.get_role(self.inquiry_message_config.role_id)

        await thread.add_user(interaction.user)
        await interaction.response.send_message(f"A new thread called {thread.mention} has been opened for this inquiry.", ephemeral=True)

        if interaction.guild.chunked is False:
            await interaction.guild.chunk(cache=True)

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

    @app_commands.command(description="Adds a message that allows users to create a private thread to open an inquiry.")
    @app_commands.describe(role="Role that has the members that should join the thread")
    async def inquiry(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        """
        Adds a message that allows users to create a private thread to open an inquiry.
        """
        if not interaction.channel.permissions_for(interaction.user).manage_threads:
            await interaction.response.send_message("You must have manage threads permission to use this feature.", ephemeral=True)
            return

        if "PRIVATE_THREADS" not in interaction.guild.features and not config.DEBUG:
            await interaction.response.send_message("Private threads must be available on this server.", ephemeral=True)
            return

        if not interaction.channel.permissions_for(interaction.guild.me).create_private_threads:
            await interaction.response.send_message("This bot needs permission to create private threads in this channel.", ephemeral=True)
            return

        if interaction.channel.permissions_for(interaction.guild.default_role).send_messages:
            await interaction.response.send_message("`@everyone` should not be allowed to send messages in this channel.", ephemeral=True)
            return

        if not interaction.channel.permissions_for(interaction.guild.default_role).send_messages_in_threads:
            await interaction.response.send_message("`@everyone` needs to be able to send messages in threads.", ephemeral=True)
            return

        if not interaction.channel.permissions_for(role).read_messages:
            await interaction.response.send_message(f"{role.mention} is not allowed to see this channel.", ephemeral=True, allowed_mentions=discord.AllowedMentions(roles=False))
            return

        await interaction.response.send_message(
            content=(
                "To **submit an inquiry**, click the 📬 button below, then click \"Yes!\" button in the next message to confirm.\n\n"
                f"This will open an inquiry visible to members of {role.mention}\n\n"
                "Thanks!"
            ),
            view=ConfirmInquiryThread(),
            allowed_mentions=discord.AllowedMentions(roles=False)
        )
        original_message = await interaction.original_response()
        await models.InquiryMessageConfig.create(message_id=original_message.id, role_id=role.id)


def check_private_threads(interaction: discord.Interaction):
    if "PRIVATE_THREADS" not in interaction.channel.guild.features:
        return False

    return True


async def setup(bot: commands.Bot):
    await bot.add_cog(Inquiry(bot))
