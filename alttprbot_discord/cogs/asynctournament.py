import asyncio
import csv
import datetime
import logging
import os
import random

import discord
import tortoise.exceptions
from discord import app_commands
from discord.ext import commands, tasks
from slugify import slugify

from alttprbot import models

APP_URL = os.environ.get('APP_URL', 'https://sahasrahbotapi.synack.live')


class AsyncTournamentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Start new async run", style=discord.ButtonStyle.green, emoji="🏁", custom_id="sahasrahbot:new_async_race")
    async def new_async_race(self, interaction: discord.Interaction, button: discord.ui.Button):
        async_tournament = await models.AsyncTournament.get_or_none(channel_id=interaction.channel_id)
        await async_tournament.fetch_related('permalink_pools')

        if async_tournament is None:
            await interaction.response.send_message("This channel is not configured for async tournaments.", ephemeral=True)
            return

        if async_tournament.active is False:
            await interaction.response.send_message("This tournament is not currently active.", ephemeral=True)
            return

        # check discord account age, this should also be configurable in the future
        # the age of the account must be at least 7 days older than the tournament start date
        if interaction.user.created_at > (async_tournament.created - datetime.timedelta(days=7)):
            await async_tournament.fetch_related('whitelist')
            if interaction.user.id not in [w.discord_user_id for w in async_tournament.whitelist]:
                await interaction.response.send_message("Your Discord account is too new to participate in this tournament.  Please contact a tournament administrator for manual verification and whitelisting.", ephemeral=True)
                return

        # this should be configurable in the future
        srlnick = await models.SRLNick.get_or_none(discord_user_id=interaction.user.id)
        if srlnick is None or srlnick.rtgg_id is None:
            await interaction.response.send_message(f"You must link your RaceTime.gg account to SahasrahBot before you can participate in an async tournament.\n\nPlease visit <{APP_URL}/racetime/verification/initiate> to link your RaceTime account.", ephemeral=True)
            return

        async_history = await models.AsyncTournamentRace.filter(discord_user_id=interaction.user.id, tournament=async_tournament).prefetch_related('permalink__pool')
        played_pools = [a.permalink.pool for a in async_history]
        available_pools = [a for a in list(async_tournament.permalink_pools) if a not in played_pools]
        if available_pools is None or len(available_pools) == 0:
            await interaction.response.send_message("You have already played all available pools for this tournament.", ephemeral=True)
            return

        await interaction.response.send_message("You must start your race within 10 minutes of clicking this button.\nFailure to do so will result in a forfeit.\n\n**Please be absolutely certain you're ready to begin.**\n\nThis dialogue box will expire in 60 seconds.  Dismiss this message if you performed this action in error.", view=AsyncTournamentRaceViewConfirmNewRace(available_pools=available_pools), ephemeral=True)

    @discord.ui.button(label="Close Async Tournament", style=discord.ButtonStyle.red, emoji="🔒", custom_id="sahasrahbot:close_async_tournament")
    async def close_async_tournament(self, interaction: discord.Interaction, button: discord.ui.Button):
        async_tournament = await models.AsyncTournament.get_or_none(channel_id=interaction.channel_id)
        if async_tournament is None:
            await interaction.response.send_message("This channel is not configured for async tournaments.", ephemeral=True)
            return

        if async_tournament.active is False:
            await interaction.response.send_message("This tournament is not currently active.", ephemeral=True)
            return

        if interaction.user.id != async_tournament.owner_id:
            await interaction.response.send_message("You are not the owner of this tournament.", ephemeral=True)
            return

        await interaction.response.send_message("Are you sure you want to close this tournament?\n\nThis action cannot be undone.", view=AsyncTournamentViewConfirmCloseTournament(view=self, interaction=interaction), ephemeral=True)


class AsyncTournamentViewConfirmCloseTournament(discord.ui.View):
    def __init__(self, view, interaction):
        super().__init__(timeout=60)
        self.original_view = view
        self.original_interaction = interaction

    @discord.ui.button(label="Yes, close this tournament", style=discord.ButtonStyle.red, emoji="🔒", row=2)
    async def async_confirm_close_tournament(self, interaction: discord.Interaction, button: discord.ui.Button):
        async_tournament = await models.AsyncTournament.get_or_none(channel_id=interaction.channel_id)
        if async_tournament is None:
            await interaction.response.send_message("This channel is not configured for async tournaments.  This should not have happened.", ephemeral=True)
            return

        if async_tournament.active is False:
            await interaction.response.send_message("This tournament is not currently active.  This should not have happened.", ephemeral=True)
            return

        if interaction.user.id != async_tournament.owner_id:
            await interaction.response.send_message("You are not the owner of this tournament.  This should not have happened.", ephemeral=True)
            return

        async_tournament.active = False
        await async_tournament.save()

        for item in self.original_view.children:
            item.disabled = True
        await self.original_interaction.followup.edit_message(message_id=self.original_interaction.message.id, view=self.original_view)

        await interaction.response.send_message("This tournament has been closed.")


class SelectPermalinkPool(discord.ui.Select):
    def __init__(self, available_pools):
        options = [discord.SelectOption(label=a.name) for a in list(available_pools)]
        super().__init__(placeholder="Select an async pool", max_values=1, min_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.pool = self.values[0]
        embed = discord.Embed(title="You have selected:", description=self.view.pool)
        for item in self.view.children:
            if item.type == discord.ComponentType.button and item.label == "I confirm, this is the point of no return!":
                item.disabled = False
        await interaction.response.edit_message(embed=embed, view=self.view)

# This view is ephemeral


class AsyncTournamentRaceViewConfirmNewRace(discord.ui.View):
    def __init__(self, available_pools):
        super().__init__(timeout=60)
        self.pool = None
        self.add_item(SelectPermalinkPool(available_pools=available_pools))

    @discord.ui.button(label="I confirm, this is the point of no return!", style=discord.ButtonStyle.green, emoji="✅", row=2, disabled=True)
    async def async_confirm_new_race(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Send a message to the thread with AsyncTournamentRaceViewReady
        # await interaction.response.send_message("NYI", ephemeral=True)
        async_tournament = await models.AsyncTournament.get_or_none(channel_id=interaction.channel_id)
        if async_tournament is None:
            await interaction.response.send_message("This channel is not configured for async tournaments.  This should not have happened.", ephemeral=True)
            return

        if async_tournament.active is False:
            await interaction.response.send_message("This tournament is not currently active.  This should not have happened.", ephemeral=True)
            return

        if self.pool is None:
            await interaction.response.send_message("Please choose a pool.", ephemeral=True)
            return

        active_races_for_user = await async_tournament.races.filter(discord_user_id=interaction.user.id, status__in=["pending", "in_progress"])
        if active_races_for_user:
            await interaction.response.send_message("You already have an active race.  If you believe this is in error, please contact a moderator.", ephemeral=True)
            return

        # Create a new private thread
        thread = await interaction.channel.create_thread(
            name=f"{slugify(interaction.user.name, lowercase=False, max_length=20)} - {self.pool}",
            type=discord.ChannelType.private_thread
        )

        pool = await async_tournament.permalink_pools.filter(name=self.pool).first()  # TODO: add a unique constraint on this

        # Double check that the player hasn't played from this pool already
        async_history = await models.AsyncTournamentRace.filter(discord_user_id=interaction.user.id, tournament=async_tournament).prefetch_related('permalink__pool')
        played_pools = [a.permalink.pool for a in async_history]
        if pool in played_pools:
            await interaction.response.send_message("You have already played from this pool.", ephemeral=True)
            return

        await pool.fetch_related("permalinks")

        # TODO: This needs to be smart by balancing the number of runs per permalink
        # Ensure we don't pick a permalink that was used in a live group race
        permalink = random.choice([p for p in pool.permalinks if not p.live_race])

        # Write the race to the database
        async_tournament_race = await models.AsyncTournamentRace.create(
            tournament=async_tournament,
            thread_id=thread.id,
            discord_user_id=interaction.user.id,
            thread_open_time=discord.utils.utcnow(),
            permalink=permalink,
        )

        # Invite the user to the thread
        await thread.add_user(interaction.user)

        # Create a post in that thread using AsyncTournamentRaceView
        embed = discord.Embed(title="Tournament Async Run")
        embed.add_field(name="Pool", value=self.pool)
        embed.add_field(name="Permalink", value=permalink.permalink)
        embed.set_footer(text=f"Race ID: {async_tournament_race.id}")
        await thread.send(embed=embed, view=AsyncTournamentRaceViewReady())
        await interaction.response.edit_message(content=f"Successfully created {thread.mention}.  Please join that thread for more details.", view=None, embed=None)

    @ discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌", row=2)
    async def async_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Successfully cancelled this request.  It will not be placed on your record and may be attempted at a later time.", view=None, embed=None)


class AsyncTournamentRaceViewReady(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ discord.ui.button(label="Ready (start countdown)", style=discord.ButtonStyle.green, emoji="✅", custom_id="sahasrahbot:async_ready")
    async def async_ready(self, interaction: discord.Interaction, button: discord.ui.Button):
        tournament_race = await models.AsyncTournamentRace.get_or_none(thread_id=interaction.channel.id)
        if tournament_race is None:
            await interaction.response.send_message("This thread is not configured for async tournaments.  This should not have happened.", ephemeral=True)
            return

        if tournament_race.discord_user_id != interaction.user.id:
            await interaction.response.send_message("Only the runner of this race can start it.", ephemeral=True)
            return

        if tournament_race.status != "pending":
            await interaction.response.send_message("This race must be in the pending state to start it.", ephemeral=True)

        await interaction.response.defer()

        for child_item in self.children:
            child_item.disabled = True
        await interaction.followup.edit_message(message_id=interaction.message.id, view=self)

        tournament_race.status = "in_progress"
        await tournament_race.save()

        for i in range(10, 0, -1):
            await interaction.channel.send(f"{i}...")
            await asyncio.sleep(1)
        await interaction.channel.send("**GO!**", view=AsyncTournamentRaceViewInProgress())
        start_time = discord.utils.utcnow()

        tournament_race.start_time = start_time
        await tournament_race.save()

    @ discord.ui.button(label="Forfeit", style=discord.ButtonStyle.red, emoji="🏳️", custom_id="sahasrahbot:async_forfeit")
    async def async_forfeit(self, interaction: discord.Interaction, button: discord.ui.Button):
        async_tournament_race = await models.AsyncTournamentRace.get_or_none(thread_id=interaction.channel.id)
        if async_tournament_race.discord_user_id != interaction.user.id:
            await interaction.response.send_message("Only the runner may forfeit this race.", ephemeral=True)
            return

        if async_tournament_race.status not in ["pending", "in_progress"]:
            await interaction.response.send_message("The race must be pending or in progress to forfeit it.", ephemeral=True)
            return

        await interaction.response.send_message("Are you sure you wish to forfeit?  Think carefully, as this action **cannot be undone**.  This race will be scored as a **zero** on your record and you may not re-play the run.", view=AsyncTournamentRaceViewForfeit(view=self, interaction=interaction), ephemeral=True)


class AsyncTournamentRaceViewInProgress(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ discord.ui.button(label="Finish", style=discord.ButtonStyle.green, emoji="✅", custom_id="sahasrahbot:async_finish")
    async def async_finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verify user clicking the button is the intended runner
        # Send a message to the thread with AsyncTournamentRaceViewFinished
        # Write the end time to database
        # Disable buttons on this view
        async_tournament_race = await models.AsyncTournamentRace.get_or_none(thread_id=interaction.channel.id)
        if async_tournament_race.discord_user_id != interaction.user.id:
            await interaction.response.send_message("Only the player of this race may finish it.", ephemeral=True)
            return

        if async_tournament_race.status != "in_progress":
            await interaction.response.send_message("You may only finish a race that's in progress.", ephemeral=True)
            return

        async_tournament_race.end_time = discord.utils.utcnow()
        async_tournament_race.status = "finished"
        await async_tournament_race.save()

        elapsed = async_tournament_race.end_time - async_tournament_race.start_time

        await interaction.response.send_message(f"Your finish time of **{elapsed}** as been recorded.  Please post the VoD of your run in this channel.")

        for child_item in self.children:
            child_item.disabled = True
        await interaction.followup.edit_message(message_id=interaction.message.id, view=self)

    @ discord.ui.button(label="Forfeit", style=discord.ButtonStyle.red, emoji="🏳️", custom_id="sahasrahbot:async_forfeit2")
    async def async_forfeit(self, interaction: discord.Interaction, button: discord.ui.Button):
        async_tournament_race = await models.AsyncTournamentRace.get_or_none(thread_id=interaction.channel.id)
        if async_tournament_race.discord_user_id != interaction.user.id:
            await interaction.response.send_message("Only the runner may forfeit this race.", ephemeral=True)
            return

        if async_tournament_race.status not in ["pending", "in_progress"]:
            await interaction.response.send_message("The race must be pending or in progress to forfeit it.", ephemeral=True)
            return

        await interaction.response.send_message("Are you sure you wish to forfeit?  Think carefully, as this action **cannot be undone**.  This race will be scored as a **zero** on your record and you may not re-play the run.", view=AsyncTournamentRaceViewForfeit(view=self, interaction=interaction), ephemeral=True)

    @ discord.ui.button(label="Get timer", style=discord.ButtonStyle.gray, emoji="⏱️", custom_id="sahasrahbot:async_get_timer")
    async def async_get_timer(self, interaction: discord.Interaction, button: discord.ui.Button):
        async_tournament_race = await models.AsyncTournamentRace.get_or_none(thread_id=interaction.channel.id)
        if async_tournament_race.status in ["forfeit", "finished"]:
            await interaction.response.send_message("Race is already finished.", ephemeral=True)
        start_time = async_tournament_race.start_time
        now = discord.utils.utcnow()
        elapsed = now - start_time
        await interaction.response.send_message(f"Timer: {elapsed}", ephemeral=True)

# This view is ephemeral


class AsyncTournamentRaceViewForfeit(discord.ui.View):
    def __init__(self, view, interaction):
        super().__init__(timeout=60)
        self.original_view = view
        self.original_interaction = interaction

    @ discord.ui.button(label="Confirm Forfeit", style=discord.ButtonStyle.red, emoji="🏳️")
    async def async_confirm_forfeit(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Write forfeit to database
        # Disable buttons on this view
        async_tournament_race = await models.AsyncTournamentRace.get_or_none(thread_id=interaction.channel.id)
        if async_tournament_race.discord_user_id != interaction.user.id:
            await interaction.response.send_message("Only the runner may forfeit this race.", ephemeral=True)
            return

        if async_tournament_race.status not in ["pending", "in_progress"]:
            await interaction.response.send_message("The race must be pending or in progress to forfeit it.", ephemeral=True)
            return

        async_tournament_race.status = "forfeit"
        await async_tournament_race.save()
        await interaction.response.send_message(f"This run has been forfeited by {interaction.user.mention}.")
        for child_item in self.children:
            child_item.disabled = True
        await interaction.followup.edit_message(message_id=interaction.message.id, view=self)

        for child_item in self.original_view.children:
            child_item.disabled = True
        await self.original_interaction.followup.edit_message(message_id=self.original_interaction.message.id, view=self.original_view)


class AsyncTournament(commands.GroupCog, name="asynctournament"):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.timeout_warning_task.start()
        self.persistent_views_added = False

    @ tasks.loop(seconds=60, reconnect=True)
    async def timeout_warning_task(self):
        try:
            pending_races = await models.AsyncTournamentRace.filter(status="pending", thread_id__isnull=False)
            for pending_race in pending_races:
                # make these configurable
                if pending_race.thread_timeout_time is None:
                    pending_race.thread_timeout_time = pending_race.thread_open_time + datetime.timedelta(minutes=20)
                    await pending_race.save()

                warning_time = pending_race.thread_timeout_time - datetime.timedelta(minutes=10)
                forfeit_time = pending_race.thread_timeout_time

                thread = self.bot.get_channel(pending_race.thread_id)
                if thread is None:
                    logging.warning("Cannot access thread for pending race %s.  This should not have happened.", pending_race.id)
                    continue

                if warning_time < discord.utils.utcnow() < forfeit_time:
                    await thread.send(f"<@{pending_race.discord_user_id}>, your race will be permanently forfeit on {discord.utils.format_dt(forfeit_time, 'f')} ({discord.utils.format_dt(forfeit_time, 'R')}) if you do not start it by then.  Please start your run as soon as possible.  Please ping the @Admins if you require more time.", allowed_mentions=discord.AllowedMentions(users=True))

                if forfeit_time < discord.utils.utcnow():
                    await thread.send(f"<@{pending_race.discord_user_id}>, the grace period for the start of this run has elapsed.  This run has been forfeit.  Please contact the @Admins if you believe this was in error.", allowed_mentions=discord.AllowedMentions(users=True))
                    pending_race.status = "forfeit"
                    await pending_race.save()
        except Exception:
            logging.exception("Exception in timeout_warning_task")

    @ timeout_warning_task.before_loop
    async def before_timeout_warning_task(self):
        await self.bot.wait_until_ready()

    @ commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.bot.add_view(AsyncTournamentView())
            self.bot.add_view(AsyncTournamentRaceViewReady())
            self.bot.add_view(AsyncTournamentRaceViewInProgress())
            self.persistent_views_added = True

    @ app_commands.command(name="create", description="Create an async tournament")
    async def create(self, interaction: discord.Interaction, name: str, permalinks: discord.Attachment, report_channel: discord.TextChannel = None):
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("Only Synack may create an async tournament at this time.", ephemeral=True)
            return

        await interaction.response.defer()
        embed = discord.Embed(title=name)
        try:
            async_tournament = await models.AsyncTournament.create(
                name=name,
                report_channel_id=report_channel.id if report_channel else None,
                active=True,
                guild_id=interaction.guild.id,
                channel_id=interaction.channel.id,
                owner_id=interaction.user.id
            )
        except tortoise.exceptions.IntegrityError:
            await interaction.followup.send("An async tournament is already associated with this channel.  Please create a new channel for the tournament or contact Synack for further assistance.", ephemeral=True)
            return

        pools = {}
        permalink_attachment = await permalinks.read()
        content = permalink_attachment.decode('utf-8-sig').splitlines()
        csv_reader = csv.reader(content)
        for row in csv_reader:
            key = row[0]
            value = row[1]
            if key not in pools:
                pools[key] = []
            pools[key].append(value)

        for pool_name, permalinks in pools.items():
            pool = await models.AsyncTournamentPermalinkPool.create(
                tournament=async_tournament,
                name=pool_name,
            )
            for permalink in permalinks:
                await models.AsyncTournamentPermalink.create(
                    pool=pool,
                    permalink=permalink,
                )

        embed = create_tournament_embed(async_tournament)
        await interaction.followup.send(embed=embed, view=AsyncTournamentView())

    @ app_commands.command(name="extendtimeout", description="Extend the timeout of this tournament run")
    async def extend_timeout(self, interaction: discord.Interaction, minutes: int):
        # TODO: replace this with a lookup on the config table for authorized users
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("Only Synack may create an async tournament at this time.", ephemeral=True)
            return

        async_tournament_race = await models.AsyncTournamentRace.get_or_none(thread_id=interaction.channel.id)
        if not async_tournament_race:
            await interaction.response.send_message("This channel is not an async tournament thread.", ephemeral=True)
            return

        if async_tournament_race.status != "pending":
            await interaction.response.send_message("This race is not pending.  It cannot be extended.", ephemeral=True)
            return

        if async_tournament_race.thread_timeout_time is None:
            thread_timeout_time = async_tournament_race.thread_open_time + datetime.timedelta(minutes=20) + datetime.timedelta(minutes=minutes)
        else:
            thread_timeout_time = async_tournament_race.thread_timeout_time + datetime.timedelta(minutes=minutes)

        async_tournament_race.thread_timeout_time = thread_timeout_time
        await async_tournament_race.save()

        await interaction.response.send_message(f"Timeout extended to {discord.utils.format_dt(thread_timeout_time, 'f')} ({discord.utils.format_dt(thread_timeout_time, 'R')}).")

    @ app_commands.command(name="repost", description="Repost the tournament embed")
    async def repost(self, interaction: discord.Interaction):
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("Only Synack may create an async tournament at this time.", ephemeral=True)
            return

        await interaction.response.defer()
        async_tournament = await models.AsyncTournament.get_or_none(channel_id=interaction.channel.id)
        if async_tournament is None:
            await interaction.followup.send("This channel is not configured for async tournaments.  Please create a new tournament.", ephemeral=True)
            return

        embed = create_tournament_embed(async_tournament)
        await interaction.followup.send(embed=embed, view=AsyncTournamentView())


def create_tournament_embed(async_tournament: models.AsyncTournament):
    embed = discord.Embed(title=async_tournament.name)
    embed.add_field(name="Owner", value=f"<@{async_tournament.owner_id}>", inline=False)
    embed.set_footer(text=f"ID: {async_tournament.id}")
    return embed


async def setup(bot: commands.Bot):
    await bot.add_cog(AsyncTournament(bot))
