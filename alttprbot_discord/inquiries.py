"""The Discord side of inquiry buttons: the channel permission checks (shared by
``/inquiry`` and the website) and posting or deleting the button message for the
website. Registered with ``alttprbot.services.inquiries`` at startup."""

import logging

import discord

from alttprbot.exceptions import InvalidInputError
from alttprbot.services import inquiries
from alttprbot.services.inquiries import Check

logger = logging.getLogger(__name__)


def channel_checks(channel, role, me, everyone) -> list[Check]:
    """What an inquiry channel needs: the bot can open private threads, the role can
    see the channel, and everyone can write in threads but not in the channel."""
    name = f"#{channel.name}"
    role_name = role.name if role.name.startswith('@') else f"@{role.name}"
    bot_can = channel.permissions_for(me)
    everyone_can = channel.permissions_for(everyone)
    return [
        Check(bot_can.create_private_threads,
              f"SahasrahBot can create private threads in {name}" if bot_can.create_private_threads else
              f"SahasrahBot needs permission to create private threads in {name}."),
        Check(channel.permissions_for(role).read_messages,
              f"{role_name} can see {name}" if channel.permissions_for(role).read_messages else
              f"{role_name} can't see {name}, so nobody would be there to answer."),
        Check(not everyone_can.send_messages,
              f"Members can't post in {name}, only press the button" if not everyone_can.send_messages else
              f"@everyone can send messages in {name}. Turn that off, or people will post there instead."),
        Check(everyone_can.send_messages_in_threads,
              "Members can send messages in threads" if everyone_can.send_messages_in_threads else
              "@everyone needs to be able to send messages in threads, or they can't write in their inquiry."),
    ]


class DiscordInquiryPoster:
    """``inquiries.Poster`` backed by the bot's gateway cache (no privileged intents)."""

    def __init__(self, bot: discord.Client):
        self.bot = bot

    def _targets(self, guild_id: int, channel_id: int, role_id: int):
        guild = self.bot.get_guild(guild_id)
        channel = guild.get_channel(channel_id) if guild else None
        role = guild.get_role(role_id) if guild else None
        if channel is None or role is None:
            raise InvalidInputError("That channel or role isn't in this server any more.")
        return guild, channel, role

    async def checks(self, guild_id: int, channel_id: int, role_id: int) -> list[Check]:  # NOSONAR
        guild, channel, role = self._targets(guild_id, channel_id, role_id)
        return channel_checks(channel, role, guild.me, guild.default_role)

    async def post(self, guild_id: int, channel_id: int, role_id: int) -> int:
        # The cog owns the message and its persistent button.
        from alttprbot_discord.cogs.inquiry import ConfirmInquiryThread, inquiry_message
        _, channel, role = self._targets(guild_id, channel_id, role_id)
        try:
            message = await channel.send(content=inquiry_message(role), view=ConfirmInquiryThread(),
                                         allowed_mentions=discord.AllowedMentions(roles=False))
        except discord.Forbidden as e:
            raise InvalidInputError("SahasrahBot isn't allowed to post in that channel.") from e
        except discord.HTTPException as e:
            logger.exception("Couldn't post an inquiry button in %s", channel_id)
            raise InvalidInputError("Discord didn't accept the post. Try again in a minute.") from e
        return message.id

    async def delete(self, channel_id: int, message_id: int) -> None:
        try:
            channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
            await channel.get_partial_message(message_id).delete()
        except discord.NotFound:
            logger.info("Inquiry message %s is already gone", message_id)
        except discord.Forbidden as e:
            raise InvalidInputError("SahasrahBot isn't allowed to delete that message. Delete it in Discord.") from e

    async def locate(self, message_id: int, role_id: int):
        guild = next((g for g in self.bot.guilds if g.get_role(role_id) is not None), None)
        if guild is None:
            return None
        # A channel made after the message can't hold it (ids grow with time).
        for channel in guild.text_channels:
            if channel.id > message_id:
                continue
            perms = channel.permissions_for(guild.me)
            if not (perms.read_messages and perms.read_message_history):
                continue
            try:
                await channel.fetch_message(message_id)
            except (discord.NotFound, discord.Forbidden):
                continue
            except discord.HTTPException:
                logger.warning("Couldn't look for inquiry message %s in %s", message_id, channel.id)
                continue
            return guild.id, channel.id
        return None


def register(bot: discord.Client) -> None:
    inquiries.register_poster(DiscordInquiryPoster(bot))
