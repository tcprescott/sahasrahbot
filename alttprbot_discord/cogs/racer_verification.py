import os
import logging
import aiohttp
import datetime
import isodate
import pytz

import discord
from discord import app_commands
from discord.ext import commands

from alttprbot import models


class RacerVerificationView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Verify your status", custom_id="racerverify:verifystatus", style=discord.ButtonStyle.primary)
    async def verify_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        racer_verification = await models.RacerVerification.get_or_none(message_id=interaction.message.id, guild_id=interaction.guild.id)

        user = await models.Users.get_or_none(discord_user_id=interaction.user.id)
        if user is None or user.rtgg_id is None:
            await interaction.response.send_message(f"Please visit https://sahasrahbotapi.synack.live/racetime/verification/initiate to verify your RaceTime.gg ID!", ephemeral=True)
            return

        try:
            rtgg_categories = racer_verification.racetime_categories.split(',')
        except AttributeError:
            rtgg_categories = []

        race_count = 0

        if racer_verification.use_alttpr_ladder:
            race_count += await get_ladder_count(interaction.user.id, days=racer_verification.time_period_days)

        if race_count < racer_verification.minimum_races:
            for rtgg_category in rtgg_categories:
                race_count += await get_racetime_count(user.rtgg_id, rtgg_category, days=racer_verification.time_period_days, max_count=racer_verification.minimum_races)

        if race_count >= racer_verification.minimum_races:
            role = interaction.guild.get_role(racer_verification.role_id)
            await interaction.user.add_roles(role, reason="Racer Verification")
            await interaction.followup.send("Congratulations!  You have been verified!", ephemeral=True)
        else:
            await interaction.followup.send("Sorry, you do not meet the requirements for verification.  If you believe this is in error, please contact a server administrator for assistance.", ephemeral=True)


class RacerVerification(commands.GroupCog, name="racerverification"):
    def __init__(self, bot):
        self.bot = bot
        self.persistent_views_added = False

    @ commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.bot.add_view(RacerVerificationView(self.bot))
            self.persistent_views_added = True

    @app_commands.command(description="Create a racer verification message.")
    async def create(self, interaction: discord.Interaction, role: discord.Role, racetime_categories: str = None, use_alttpr_ladder: bool = False, minimum_races: int = 1, time_period_days: int = 365):
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("You are not the owner of this server.", ephemeral=True)
            return

        racer_verification = await models.RacerVerification.create(
            message_id=None,
            guild_id=interaction.guild.id,
            role_id=role.id,
            racetime_categories=racetime_categories,
            use_alttpr_ladder=use_alttpr_ladder,
            minimum_races=minimum_races,
            time_period_days=time_period_days
        )

        await interaction.response.send_message(view=RacerVerificationView(self.bot))
        message = await interaction.original_response()
        racer_verification.message_id = message.id
        await racer_verification.save()


async def get_racetime_count(racetime_id, category_slugs=None, days=365, max_count=1):
    page = 1
    count = 0
    if category_slugs is None:
        return 0

    while count < max_count:
        async with aiohttp.request(
            method='get',
            url=f'https://racetime.gg/user/{racetime_id}/races/data',
            params={'page': page}
        ) as resp:
            data = await resp.json()
            if len(data) == 0:
                break

            filtered_data = [x for x in data['races']
                             if x['category']['slug'] in category_slugs
                             and x['status']['value'] == 'finished'
                             and isodate.parse_datetime(x['opened_at']) > datetime.datetime.now() - datetime.timedelta(days=days)
                             ]

            count += len(filtered_data)

            if page > data['num_pages']:
                break

        page += 1

    return count


async def get_ladder_count(discord_id, days=365):
    now = datetime.datetime.now()
    delta = datetime.timedelta(days=days)
    start = (now - delta).strftime('%m%d%Y')
    end = now.strftime('%m%d%Y')
    async with aiohttp.request(
        method='get',
        url=f'https://alttprladder.com/api/v1/PublicAPI/GetRacerRaceHistory?discordid={discord_id}&startdt={start}&enddt={end}',
        headers={'User-Agent': 'SahasrahBot'},
        raise_for_status=True
    ) as resp:
        data = await resp.json()

    return data['TotalCount']


async def setup(bot: commands.Bot):
    await bot.add_cog(RacerVerification(bot))
