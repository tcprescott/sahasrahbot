import datetime
from typing import List
from io import StringIO

import aiohttp
import discord
import isodate
import pytz
from discord import app_commands
from discord.ext import commands, tasks

import config
from alttprbot import models

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

        eligible, count = await determine_eligibility(user, racer_verification)

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
        # self.reverify_racer.start() # pylint: disable=no-member

    @tasks.loop(minutes=1 if config.DEBUG else 1440, reconnect=True)
    async def reverify_racer(self):
        racer_verifications = await models.RacerVerification.all()
        for racer_verification in racer_verifications:
            revoked_users = await self.reverify_racer_verification(racer_verification, revoke=racer_verification.revoke_ineligible)

            if revoked_users:
                guild = self.bot.get_guild(racer_verification.guild_id)
                audit_channel = guild.get_channel(racer_verification.audit_channel_id)
                if audit_channel is not None:
                    # attach a list of users who were revoked
                    revoked_users_list = '\n'.join([x.user.display_name for x in revoked_users])
                    if len(revoked_users_list) > 1800:
                        # attach the list as a file if it's too long
                        await audit_channel.send(
                            f"**{len(revoked_users)}** users were revoked from the {guild.get_role(racer_verification.role_id).name} role due to ineligibility.",
                            file=discord.File(fp=StringIO(revoked_users_list), filename="revoked_users.txt"))
                    else:
                        await audit_channel.send(
                            f"**{len(revoked_users)}** users were revoked from the {guild.get_role(racer_verification.role_id).name} role due to ineligibility.\n\n{revoked_users_list}")

    @reverify_racer.before_loop
    async def before_create_races(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.bot.add_view(RacerVerificationView(self.bot))
            self.persistent_views_added = True

    @app_commands.command(description="Reverify all racers in this server.")
    async def reverify(self, interaction: discord.Interaction, revoke: bool=False):
        if interaction.user.guild_permissions.administrator is False and self.bot.is_owner(interaction.user) is False:
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        racer_verifications = await models.RacerVerification.filter(guild_id=interaction.guild.id)
        for racer_verification in racer_verifications:
            revoked_users = await self.reverify_racer_verification(racer_verification, revoke=revoke)
            racer_verification_role = interaction.guild.get_role(racer_verification.role_id)

            if revoked_users:
                # attach a list of users who were revoked
                revoked_users_list = '\n'.join([x.user.display_name for x in revoked_users])
                if len(revoked_users_list) > 1800:
                    # attach the list as a file if it's too long
                    await interaction.followup.send(
                        f"**{len(revoked_users)}** users were revoked from the {racer_verification_role.mention} role due to ineligibility.",
                        file=discord.File(fp=StringIO(revoked_users_list), filename="revoked_users.txt"),
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"**{len(revoked_users)}** users were revoked from the {racer_verification_role.mention} role due to ineligibility.\n\n{revoked_users_list}",
                        ephemeral=True
                    )
            else:
                await interaction.followup.send(
                    f"No users were revoked from the {racer_verification_role.mention} role due to ineligibility.",
                    ephemeral=True
                )


    @app_commands.command(description="Create a racer verification message.")
    async def create(self, interaction: discord.Interaction, role: discord.Role, racetime_categories: str = None,
                     use_alttpr_ladder: bool = False, minimum_races: int = 1, time_period_days: int = 365):
        if interaction.user.guild_permissions.administrator is False and self.bot.is_owner(interaction.user) is False:
            await interaction.response.send_message("You are authorized to use this command.", ephemeral=True)
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
        await racer_verification.save()

    async def reverify_racer_verification(self, racer_verification: models.RacerVerification, revoke=False):
        if racer_verification.reverify_period_days is None:
            # skip this as this racer verification is not set to reverify
            return False

        # get all racers with this role
        guild = self.bot.get_guild(racer_verification.guild_id)

        # chunk the guild if it hasn't been done yet
        if guild.chunked is False:
            await guild.chunk(cache=True)

        verified_racer_role = guild.get_role(racer_verification.role_id)

        revoked_users: List[models.VerifiedRacer] = []

        for verified_racer_member in verified_racer_role.members:
            # create database records if they don't already exist
            verified_racer_user, _ = await models.Users.get_or_create(
                discord_user_id=verified_racer_member.id,
                defaults={
                    'display_name': verified_racer_member.name,
                }
            )
            verified_racer, _ = await models.VerifiedRacer.get_or_create(
                user=verified_racer_user,
                defaults={
                    'racer_verification': racer_verification,
                }
            )
            verified_racer.fetch_related('user')

            # check if they're required to reverify
            if verified_racer.last_verified is not None and discord.utils.utcnow() - verified_racer.last_verified < datetime.timedelta(days=racer_verification.reverify_period_days):
                # skip this racer as they're not due for reverification
                continue
            
            # check if they still meet the requirements
            eligible, count = await determine_eligibility(verified_racer_user, racer_verification)

            if eligible:
                verified_racer.estimated_count = count
                verified_racer.last_verified = discord.utils.utcnow()
                await verified_racer.save()
            else:
                revoked_users.append(verified_racer_user)
                if revoke:
                    # remove the role
                    await verified_racer_member.remove_roles(verified_racer_role, reason="Racer Verification")
                    # delete the database record
                    await verified_racer.delete()
                    # send a message to the user
                    await verified_racer_member.send(
                        f"Your verification for __{verified_racer_role.name} has expired.  Please re-verify by clicking the button in the message in the {guild.name} server.\n\nIf you believe this is in error, please contact a server administrator for assistance."
                    )

        return revoked_users

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
                                                       datetime.datetime.utcnow() - datetime.timedelta(days=days))
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

async def determine_eligibility(user: models.Users, racer_verification: models.RacerVerification):
    try:
        rtgg_categories = racer_verification.racetime_categories.split(',')
    except AttributeError:
        rtgg_categories = []

    race_count = 0

    if racer_verification.use_alttpr_ladder:
        race_count += await get_ladder_count(user.id, days=racer_verification.time_period_days)

    if race_count < racer_verification.minimum_races:
        race_count += await get_racetime_count(user.rtgg_id, rtgg_categories,
                                                days=racer_verification.time_period_days,
                                                max_count=racer_verification.minimum_races)

    return race_count >= racer_verification.minimum_races, race_count



async def setup(bot: commands.Bot):
    await bot.add_cog(RacerVerification(bot))
