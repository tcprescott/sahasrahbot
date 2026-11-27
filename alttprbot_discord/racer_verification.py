"""Racer verification on Discord: the "Verify your status" button, and the Discord
side of ``alttprbot.services.racer_verification`` (posting the message, removing
roles), registered as its gateway at startup. Needs no privileged intents.
"""

import logging
from typing import Optional

import discord
from discord.ext import commands

from alttprbot.exceptions import InvalidInputError
from alttprbot.services import racer_verification as verification
from alttprbot_discord.audit import audited

logger = logging.getLogger(__name__)

VERIFY_BUTTON_ID = "racerverify:verifystatus"  # unchanged, so buttons on old messages keep working


class RacerVerificationView(discord.ui.View):
    def __init__(self, bot: Optional[commands.Bot] = None):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Verify your status", custom_id=VERIFY_BUTTON_ID,
                       style=discord.ButtonStyle.primary)
    @audited('Verify your status button')
    async def verify_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        racer_verification = await verification.get_for_message(interaction.message.id, interaction.guild.id)

        if racer_verification is None:
            await interaction.followup.send(
                "This message is not a valid racer verification message.  This should not have happened.",
                ephemeral=True)
            return

        user = await verification.get_linked_user(interaction.user.id)
        if user is None:
            await interaction.followup.send(
                "Please visit https://sahasrahbotapi.synack.live/racetime/verification/initiate to link your RaceTime.gg ID!\n\nAfter that, click the button again!",
                ephemeral=True)
            return

        eligible, count = await verification.determine_eligibility(interaction.user.name, user, racer_verification)

        if eligible:
            await verification.record_verified(user, racer_verification, count)

            role = interaction.guild.get_role(racer_verification.role_id)
            await interaction.user.add_roles(role, reason="Racer Verification")
            await interaction.followup.send(f"Congratulations!  You have been verified!\n\nWe counted at least **{count}** races played over the last **{racer_verification.time_period_days}** days.", ephemeral=True)
        else:
            await interaction.followup.send(
                "Sorry, you do not meet the requirements for verification.  If you believe this is in error, please contact a server administrator for assistance.",
                ephemeral=True)


class DiscordGateway:
    """``racer_verification.Gateway`` backed by the bot."""

    def __init__(self, bot: discord.Client):
        self.bot = bot

    async def _channel(self, channel_id: int):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            channel = await self.bot.fetch_channel(channel_id)
        return channel

    async def _guild(self, guild_id: int) -> discord.Guild:
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            guild = await self.bot.fetch_guild(guild_id)
        return guild

    async def post_message(self, channel_id: int, content: str) -> int:
        try:
            channel = await self._channel(channel_id)
            message = await channel.send(content=content, view=RacerVerificationView(self.bot))
        except discord.Forbidden as e:
            raise InvalidInputError("SahasrahBot isn't allowed to post in that channel.") from e
        except discord.HTTPException as e:
            logger.exception("Couldn't post a racer verification message in %s", channel_id)
            raise InvalidInputError("Discord didn't accept the post. Try again in a minute.") from e
        return message.id

    async def edit_message(self, channel_id: int, message_id: int, content: str) -> bool:
        try:
            channel = await self._channel(channel_id)
            await channel.get_partial_message(message_id).edit(content=content, view=RacerVerificationView(self.bot))
        except discord.NotFound:
            return False
        return True

    async def delete_message(self, channel_id: int, message_id: int) -> None:
        try:
            channel = await self._channel(channel_id)
            await channel.get_partial_message(message_id).delete()
        except (discord.NotFound, discord.Forbidden):
            pass

    async def member_name(self, guild_id: int, user_id: int) -> Optional[str]:
        # Unlike discord_members.get_member, any error other than "not a member" raises,
        # so a Discord hiccup is never taken for someone having left.
        guild = await self._guild(guild_id)
        member = guild.get_member(user_id)
        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except discord.NotFound:
                return None
        return member.name

    async def remove_role(self, guild_id: int, user_id: int, role_id: int, reason: str) -> None:
        guild = await self._guild(guild_id)
        try:
            member = guild.get_member(user_id) or await guild.fetch_member(user_id)
            await member.remove_roles(discord.Object(id=role_id), reason=reason)
        except discord.NotFound:
            pass  # they left, or the role is gone
        except discord.Forbidden as e:
            raise InvalidInputError(
                "SahasrahBot isn't allowed to remove that role. Move its role above the verified role.") from e


def register(bot: discord.Client) -> None:
    verification.register(DiscordGateway(bot))
