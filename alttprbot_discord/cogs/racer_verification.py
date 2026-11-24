from datetime import datetime
from datetime import timedelta
import aiohttp
import discord
import isodate
import pytz
from discord import app_commands
from discord.ext import commands

import config
from alttprbot import models
from alttprbot.util import discord_members

RACETIME_URL = config.RACETIME_URL


class RacerVerificationView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Verify your status", custom_id="racerverify:verifystatus",
                       style=discord.ButtonStyle.primary)
    async def verify_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        racer_verification = await models.RacerVerification.get_or_none(message_id=interaction.message.id,
                                                                        guild_id=interaction.guild.id)

        if racer_verification is None:
            await interaction.followup.send(
                "This message is not a valid racer verification message.  This should not have happened.",
                ephemeral=True)
            return

        user = await models.Users.get_or_none(discord_user_id=interaction.user.id)
        if user is None or user.rtgg_id is None:
            await interaction.followup.send(
                "Please visit https://sahasrahbotapi.synack.live/racetime/verification/initiate to link your RaceTime.gg ID!\n\nAfter that, click the button again!",
                ephemeral=True)
            return

        eligible, count = await determine_eligibility(interaction.user.name, user, racer_verification)

        if eligible:
            racer = await models.VerifiedRacer.get_or_none(
                user=user,
                racer_verification=racer_verification
            )
            if racer is None:
                racer = await models.VerifiedRacer.create(
                    user=user,
                    racer_verification=racer_verification,
                    last_verified=discord.utils.utcnow(),
                    estimated_count=count
                )
            else:
                racer.last_verified = discord.utils.utcnow()
                racer.estimated_count = count
                await racer.save()

            role = interaction.guild.get_role(racer_verification.role_id)
            await interaction.user.add_roles(role, reason="Racer Verification")
            await interaction.followup.send(f"Congratulations!  You have been verified!\n\nWe counted at least **{count}** races played over the last **{racer_verification.time_period_days}** days.", ephemeral=True)
        else:
            await interaction.followup.send(
                "Sorry, you do not meet the requirements for verification.  If you believe this is in error, please contact a server administrator for assistance.",
                ephemeral=True)


class RacerVerification(commands.GroupCog, name="racerverification"):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.persistent_views_added = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.bot.add_view(RacerVerificationView(self.bot))
            self.persistent_views_added = True

    @app_commands.command(description="Create a racer verification message.")
    @app_commands.describe(role="The role to assign to verified racers.")
    @app_commands.describe(racetime_categories="A comma-separated list of racetime categories to include in verification.")
    @app_commands.describe(use_alttpr_ladder="Set to true to include ALTTPR ladder in the verification requirements.")
    @app_commands.describe(minimum_races="Minimum number of races required to be verified.")
    @app_commands.describe(time_period_days="How long back to look to verify the racer.")
    @app_commands.describe(reverify_period_days="How often should the racer be required to reverify.  Leave blank to disable reverification.")
    @app_commands.describe(revoke_ineligible="Set to true to revoke the role from ineligible racers.")
    @app_commands.describe(audit_channel="Set to a channel to send a message to when a racer is revoked.")
    async def create_or_update(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        racetime_categories: str = None,
        use_alttpr_ladder: bool = False,
        minimum_races: int = 1,
        time_period_days: int = 365,
        reverify_period_days: int = None,
        revoke_ineligible: bool = False,
        audit_channel: discord.TextChannel = None,
    ):
        if interaction.user.guild_permissions.administrator is False and self.bot.is_owner(interaction.user) is False:
            await interaction.response.send_message("You are authorized to use this command.", ephemeral=True)
            return

        racer_verification, _ = await models.RacerVerification.update_or_create(
            role_id=role.id,
            guild_id=interaction.guild.id,
            defaults={
                'racetime_categories': racetime_categories,
                'use_alttpr_ladder': use_alttpr_ladder,
                'minimum_races': minimum_races,
                'time_period_days': time_period_days,
                'reverify_period_days': reverify_period_days,
                'revoke_ineligible': revoke_ineligible,
                'audit_channel_id': audit_channel.id if audit_channel else None,
            }
        )

        rtgg_categories = racetime_categories.split(',') if racetime_categories is not None else []

        content = f"""
This message will be used to verify your status as a racer. You can click the button below to verify your status.
You must have a RaceTime.gg account linked to your Discord account to use this feature.
If you do not have a RaceTime.gg account, please visit <https://racetime.gg> to create one.

If you have any questions, please contact a server administrator.

**Requirements:**
- Must have a RaceTime.gg account linked to your Discord account via SahasrahBot.  You will be supplied a link to do so if this is not already done.
- Have at least {minimum_races} {'race' if minimum_races == 1 else 'races'} played in the last {time_period_days} {'day' if time_period_days == 1 else 'days'} on RaceTime.gg in the following categories: {', '.join(rtgg_categories)}{' or ALTTPR Ladder races ' if use_alttpr_ladder else ''}
- Must be a member of this Discord server
"""


        await interaction.response.send_message(
            content=content,
            view=RacerVerificationView(self.bot)
        )
        message = await interaction.original_response()
        racer_verification.message_id = message.id
        racer_verification.channel_id = message.channel.id
        await racer_verification.save()

async def get_racetime_count(racetime_id, category_slugs=None, days=365, max_count=1):
    page = 1
    count = 0
    if category_slugs is None:
        return 0

    while count < max_count:
        async with aiohttp.request(
                method='get',
                url=f'{RACETIME_URL}/user/{racetime_id}/races/data',
                params={'page': page}
        ) as resp:
            try:
                data = await resp.json()
            except aiohttp.ContentTypeError:
                break

            if len(data['races']) == 0:
                break

            filtered_data = [x for x in data['races']
                             if x['category']['slug'] in category_slugs
                             and x['status']['value'] == 'finished'
                             and tz_aware_greater_than(isodate.parse_datetime(x['opened_at']),
                                                       datetime.utcnow() - timedelta(days=days))
                             ]

            count += len(filtered_data)

            if page > data['num_pages']:
                break

        page += 1

    return count


def tz_aware_greater_than(dt1, dt2):
    if dt1.tzinfo is None:
        dt1 = pytz.utc.localize(dt1)
    if dt2.tzinfo is None:
        dt2 = pytz.utc.localize(dt2)
    return dt1 > dt2

async def get_ladder_guid(discord_username):
    async with aiohttp.request(
            method='get',
            url='https://alttprladder.com/api/v1/PublicAPI/GetActiveRacers',
            headers={'User-Agent': 'SahasrahBot'},
            raise_for_status=True
    ) as resp:
        data = await resp.json()

    for racer in data:
        if racer['DiscordName'] == discord_username:
            return racer['RacerGUID']

async def get_ladder_count(discord_username, days=365):
    racer_guid = await get_ladder_guid(discord_username)
    async with aiohttp.request(
            method='get',
            url=f'https://alttprladder.com/api/v1/PublicAPI/GetRacerHistory?RacerGUID={racer_guid}&flag_id=0',
            headers={'User-Agent': 'SahasrahBot'},
            raise_for_status=True
    ) as resp:
        data = await resp.json()

    cutoff = datetime.now() - timedelta(days=days)
    total = sum(
       len([race for race in flag['Results'] 
            if datetime.fromisoformat(race['StartDateTime']) > cutoff])
       for flag in data
    )
    return total

# This method will be deprecated in the future once we've had ladder 2.0 for a year.
async def get_ladder_archive_count(discord_id, days=365):
    now = datetime.now()
    delta = timedelta(days=days)
    start = (now - delta).strftime('%m%d%Y')
    end = now.strftime('%m%d%Y')
    async with aiohttp.request(
            method='get',
            url=f'https://archive.alttprladder.com/api/v1/PublicAPI/GetRacerRaceHistory?discordid={discord_id}&startdt={start}&enddt={end}',
            headers={'User-Agent': 'SahasrahBot'},
            raise_for_status=True
    ) as resp:
        data = await resp.json()

    return data['TotalCount']

async def determine_eligibility(username: str, user: models.Users, racer_verification: models.RacerVerification):
    try:
        rtgg_categories = racer_verification.racetime_categories.split(',')
    except AttributeError:
        rtgg_categories = []

    race_count = 0

    
    if racer_verification.use_alttpr_ladder:
         race_count += await get_ladder_count(username, days=racer_verification.time_period_days)
         race_count += await get_ladder_archive_count(user.discord_user_id, days=racer_verification.time_period_days)

    if race_count < racer_verification.minimum_races:
        race_count += await get_racetime_count(user.rtgg_id, rtgg_categories,
                                                days=racer_verification.time_period_days,
                                                max_count=racer_verification.minimum_races)

    return race_count >= racer_verification.minimum_races, race_count



async def setup(bot: commands.Bot):
    await bot.add_cog(RacerVerification(bot))
