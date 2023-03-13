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
from tortoise.functions import Count

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
            await async_tournament.fetch_related('whitelist', 'whitelist__user')
            if interaction.user.id not in [w.user.discord_user_id for w in async_tournament.whitelist]:
                await interaction.response.send_message("Your Discord account is too new to participate in this tournament.  Please contact a tournament administrator for manual verification and whitelisting.", ephemeral=True)
                return

        # this should be configurable in the future
        user, _ = await models.Users.get_or_create(discord_user_id=interaction.user.id)
        if user.rtgg_id is None:
            await interaction.response.send_message(f"You must link your RaceTime.gg account to SahasrahBot before you can participate in an async tournament.\n\nPlease visit <{APP_URL}/racetime/verification/initiate> to link your RaceTime account.", ephemeral=True)
            return

        async_history = await models.AsyncTournamentRace.filter(user=user, tournament=async_tournament).prefetch_related('permalink__pool')
        played_pools = [a.permalink.pool for a in async_history if a.reattempted is False]
        available_pools = [a for a in list(async_tournament.permalink_pools) if a not in played_pools]
        if available_pools is None or len(available_pools) == 0:
            await interaction.response.send_message("You have already played all available pools for this tournament.", ephemeral=True)
            return

        await interaction.response.send_message("You must start your race within 10 minutes of clicking this button.\nFailure to do so will result in a forfeit.\n\n**Please be absolutely certain you're ready to begin.**\n\nThis dialogue box will expire in 60 seconds.  Dismiss this message if you performed this action in error.", view=AsyncTournamentRaceViewConfirmNewRace(available_pools=available_pools), ephemeral=True)

    @discord.ui.button(label="Re-attempt", style=discord.ButtonStyle.blurple, emoji="↩️", custom_id="sahasrahbot:async_reattempt")
    async def async_reattempt(self, interaction: discord.Interaction, button: discord.ui.Button):
        async_tournament = await models.AsyncTournament.get_or_none(channel_id=interaction.channel_id)
        await async_tournament.fetch_related('permalink_pools')

        if async_tournament is None:
            await interaction.response.send_message("This channel is not configured for async tournaments.", ephemeral=True)
            return

        if async_tournament.active is False:
            await interaction.response.send_message("This tournament is not currently active.", ephemeral=True)
            return

        if async_tournament.allowed_reattempts is None or async_tournament.allowed_reattempts == 0:
            await interaction.response.send_message("This tournament does not allow re-attempts.", ephemeral=True)
            return

        user, _ = await models.Users.get_or_create(discord_user_id=interaction.user.id)

        async_history = await models.AsyncTournamentRace.filter(user=user, tournament=async_tournament).prefetch_related('permalink__pool')
        played_pools = [a.permalink.pool for a in async_history if a.reattempted is False]
        if played_pools is None or len(played_pools) == 0:
            await interaction.response.send_message("You have not yet played any pools for this tournament.", ephemeral=True)
            return

        reattempts = [a for a in async_history if a.reattempted is True]

        available_reattempts = async_tournament.allowed_reattempts - len(reattempts)

        if available_reattempts < 1:
            await interaction.response.send_message(f"You have already used all of your re-attempts for this tournament.", ephemeral=True)
            return

        await interaction.response.send_message(f"Please choose a pool to reattempt.  You have **{available_reattempts}** re-attempts remaining.", view=AsyncTournamentRaceViewConfirmReattempt(played_pools=played_pools), ephemeral=True)

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
    def __init__(self, pools):
        options = [discord.SelectOption(label=a.name) for a in list(pools)]
        super().__init__(placeholder="Select an async pool", max_values=1, min_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.pool = self.values[0]
        embed = discord.Embed(title="You have selected:", description=self.view.pool)
        for item in self.view.children:
            if item.type == discord.ComponentType.button:
                item.disabled = False
        await interaction.response.edit_message(embed=embed, view=self.view)

# This view is ephemeral


class AsyncTournamentRaceViewConfirmNewRace(discord.ui.View):
    def __init__(self, available_pools):
        super().__init__(timeout=60)
        self.pool = None
        self.add_item(SelectPermalinkPool(pools=available_pools))

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

        active_races_for_user = await async_tournament.races.filter(user__discord_user_id=interaction.user.id, status__in=["pending", "in_progress"])
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
        async_history = await models.AsyncTournamentRace.filter(user__discord_user_id=interaction.user.id, tournament=async_tournament).prefetch_related('permalink__pool')
        played_pools = [a.permalink.pool for a in async_history if a.reattempted is False]
        if pool in played_pools:
            await interaction.response.send_message("You have already played from this pool.", ephemeral=True)
            return

        await pool.fetch_related("permalinks")

        # TODO: This needs to be smart by balancing the number of runs per permalink
        # Ensure we don't pick a permalink that was used in a live group race

        permalink_counts = await models.AsyncTournamentRace.filter(tournament=async_tournament, permalink__pool=pool).annotate(count=Count('permalink_id')).group_by("permalink_id").values("permalink_id", "count")
        permalink_count_dict = {item['permalink_id']: item['count'] for item in permalink_counts}
        permalink_count_dict = {p.id: permalink_count_dict.get(p.id, 0) for p in pool.permalinks if p.live_race is False}

        player_async_history = await models.AsyncTournamentRace.filter(user__discord_user_id=interaction.user.id, tournament=async_tournament, permalink__pool=pool).prefetch_related('permalink')
        available_permalinks = await pool.permalinks.filter(live_race=False)
        played_permalinks = [p.permalink for p in player_async_history]
        eligible_permalinks = list(set(available_permalinks) - set(played_permalinks))

        if max(permalink_count_dict.values()) - min(permalink_count_dict.values()) > 10:
            # pool is unbalanced, so we need to pick a permalink that has been played the least
            permalink_id = min(permalink_count_dict, key=permalink_count_dict.get)
            # ensure it's eligible to be played
            if permalink_id in [e.id for e in eligible_permalinks]:
                permalink = await models.AsyncTournamentPermalink.get(id=permalink_id)
            else:
                # pick a random eligible permalink instead of the one we need to force, because the one we're forcing is not eligible
                permalink: models.AsyncTournamentPermalink = random.choice(eligible_permalinks)
        else:
            permalink: models.AsyncTournamentPermalink = random.choice(eligible_permalinks)

        user, _ = await models.Users.get_or_create(discord_user_id=interaction.user.id)

        # Log the action
        await models.AsyncTournamentAuditLog.create(
            tournament=async_tournament,
            user=user,
            action="create_thread",
            details=f"Created thread {thread.id} for pool {pool.name}, permalink {permalink.url}"
        )

        # Write the race to the database
        async_tournament_race = await models.AsyncTournamentRace.create(
            tournament=async_tournament,
            thread_id=thread.id,
            user=user,
            thread_open_time=discord.utils.utcnow(),
            permalink=permalink,
        )

        # Invite the user to the thread
        await thread.add_user(interaction.user)

        # Create a post in that thread using AsyncTournamentRaceView
        embed = discord.Embed(title="Tournament Async Run")
        embed.add_field(name="Pool", value=self.pool, inline=False)
        embed.add_field(name="Permalink", value=permalink.url, inline=False)
        if permalink.notes:
            embed.add_field(name="Notes", value=permalink.notes, inline=False)
        embed.set_footer(text=f"Race ID: {async_tournament_race.id}")
        await thread.send(embed=embed, view=AsyncTournamentRaceViewReady())
        await interaction.response.edit_message(content=f"Successfully created {thread.mention}.  Please join that thread for more details.", view=None, embed=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌", row=2)
    async def async_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Successfully cancelled this request.  It will not be placed on your record and may be attempted at a later time.", view=None, embed=None)


class AsyncTournamentRaceViewConfirmReattempt(discord.ui.View):
    def __init__(self, played_pools):
        super().__init__(timeout=60)
        self.pool = None
        self.add_item(SelectPermalinkPool(pools=played_pools))

    @discord.ui.button(label="I confirm!  I will not be allowed to undo this decision.", style=discord.ButtonStyle.green, emoji="✅", row=2, disabled=True)
    async def async_confirm_new_race(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Send a message to the thread with AsyncTournamentRaceViewReady
        async_tournament = await models.AsyncTournament.get_or_none(channel_id=interaction.channel_id)
        if async_tournament is None:
            await interaction.response.send_message("This channel is not configured for async tournaments.  This should not have happened.", ephemeral=True)
            return

        if async_tournament.active is False:
            await interaction.response.send_message("This tournament is not currently active.  This should not have happened.", ephemeral=True)
            return

        if async_tournament.allowed_reattempts is None or async_tournament.allowed_reattempts == 0:
            await interaction.response.send_message("This tournament does not allow re-attempts.  This should not have happened.", ephemeral=True)
            return

        if self.pool is None:
            await interaction.response.send_message("Please choose a pool.", ephemeral=True)
            return

        user, _ = await models.Users.get_or_create(discord_user_id=interaction.user.id)

        active_races_for_user = await async_tournament.races.filter(user=user, status__in=["pending", "in_progress"])
        if active_races_for_user:
            await interaction.response.send_message("You already have an active race.  If you believe this is in error, please contact a moderator.", ephemeral=True)
            return

        previous_tournament_races_for_pool = await models.AsyncTournamentRace.filter(user=user, tournament=async_tournament, permalink__pool__name=self.pool).prefetch_related('permalink__pool')
        for race in previous_tournament_races_for_pool:
            await models.AsyncTournamentAuditLog.create(
                tournament=async_tournament,
                user=user,
                action="reattempt",
                details=f"Marked {race.id} as a re-attempt for pool {self.pool}"
            )
            race.reattempted = True
            await race.save()

        await interaction.response.edit_message(content="Successfully marked your previous race in this pool as a re-attempt.  Please choose a new permalink.", view=None, embed=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌", row=2)
    async def async_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Successfully cancelled this request.  You have not used a re-attempt.", view=None, embed=None)


class AsyncTournamentRaceViewReady(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ready (start countdown)", style=discord.ButtonStyle.green, emoji="✅", custom_id="sahasrahbot:async_ready")
    async def async_ready(self, interaction: discord.Interaction, button: discord.ui.Button):
        tournament_race = await models.AsyncTournamentRace.get_or_none(thread_id=interaction.channel.id).prefetch_related('user')
        if tournament_race is None:
            await interaction.response.send_message("This thread is not configured for async tournaments.  This should not have happened.", ephemeral=True)
            return

        user, _ = await models.Users.get_or_create(discord_user_id=interaction.user.id)

        if tournament_race.user.discord_user_id != interaction.user.id:
            await interaction.response.send_message("Only the runner of this race can start it.", ephemeral=True)
            return

        if tournament_race.status != "pending":
            await interaction.response.send_message("This race must be in the pending state to start it.", ephemeral=True)

        await interaction.response.defer()

        await models.AsyncTournamentAuditLog.create(
            tournament_id=tournament_race.tournament_id,
            user=user,
            action="race_ready",
            details=f"{tournament_race.id} is marked as ready"
        )

        for child_item in self.children:
            child_item.disabled = True
        await interaction.followup.edit_message(message_id=interaction.message.id, view=self)

        tournament_race.status = "in_progress"
        await tournament_race.save()

        await models.AsyncTournamentAuditLog.create(
            tournament_id=tournament_race.tournament_id,
            user=user,
            action="race_countdown",
            details=f"{tournament_race.id} is starting a countdown"
        )

        for i in range(10, 0, -1):
            await interaction.channel.send(f"{i}...")
            await asyncio.sleep(1)
        await interaction.channel.send("**GO!**", view=AsyncTournamentRaceViewInProgress())
        start_time = discord.utils.utcnow()

        tournament_race.start_time = start_time
        await tournament_race.save()

        await models.AsyncTournamentAuditLog.create(
            tournament_id=tournament_race.tournament_id,
            user=user,
            action="race_started",
            details=f"{tournament_race.id} has started"
        )

    @discord.ui.button(label="Forfeit", style=discord.ButtonStyle.red, emoji="🏳️", custom_id="sahasrahbot:async_forfeit")
    async def async_forfeit(self, interaction: discord.Interaction, button: discord.ui.Button):
        async_tournament_race = await models.AsyncTournamentRace.get_or_none(thread_id=interaction.channel.id).prefetch_related('user')
        if async_tournament_race.user.discord_user_id != interaction.user.id:
            await interaction.response.send_message("Only the runner may forfeit this race.", ephemeral=True)
            return

        if async_tournament_race.status not in ["pending", "in_progress"]:
            await interaction.response.send_message("The race must be pending or in progress to forfeit it.", ephemeral=True)
            return

        await interaction.response.send_message("Are you sure you wish to forfeit?  Think carefully, as this action **cannot be undone**.  This race will be scored as a **zero** on your record and you may not re-play the run.", view=AsyncTournamentRaceViewForfeit(view=self, interaction=interaction), ephemeral=True)


class AsyncTournamentRaceViewInProgress(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Finish", style=discord.ButtonStyle.green, emoji="✅", custom_id="sahasrahbot:async_finish")
    async def async_finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        await finish_race(interaction)

        for child_item in self.children:
            child_item.disabled = True
        await interaction.followup.edit_message(message_id=interaction.message.id, view=self)

    @discord.ui.button(label="Forfeit", style=discord.ButtonStyle.red, emoji="🏳️", custom_id="sahasrahbot:async_forfeit2")
    async def async_forfeit(self, interaction: discord.Interaction, button: discord.ui.Button):
        async_tournament_race = await models.AsyncTournamentRace.get_or_none(thread_id=interaction.channel.id).prefetch_related('user')
        if async_tournament_race.user.discord_user_id != interaction.user.id:
            await interaction.response.send_message("Only the runner may forfeit this race.", ephemeral=True)
            return

        if async_tournament_race.status not in ["pending", "in_progress"]:
            await interaction.response.send_message("The race must be pending or in progress to forfeit it.", ephemeral=True)
            return

        await interaction.response.send_message("Are you sure you wish to forfeit?  Think carefully, as this action **cannot be undone**.  This race will be scored as a **zero** on your record and you may not re-play the run.", view=AsyncTournamentRaceViewForfeit(view=self, interaction=interaction), ephemeral=True)

    @discord.ui.button(label="Get timer", style=discord.ButtonStyle.gray, emoji="⏱️", custom_id="sahasrahbot:async_get_timer")
    async def async_get_timer(self, interaction: discord.Interaction, button: discord.ui.Button):
        async_tournament_race = await models.AsyncTournamentRace.get_or_none(thread_id=interaction.channel.id)
        if async_tournament_race.status in ["forfeit", "finished"]:
            await interaction.response.send_message("Race is already finished.", ephemeral=True)
            return
        start_time = async_tournament_race.start_time
        now = discord.utils.utcnow()
        elapsed = now - start_time
        await interaction.response.send_message(f"Timer: **{elapsed_time_hhmmss(elapsed)}**", ephemeral=True)


class AsyncTournamentRaceViewForfeit(discord.ui.View):
    def __init__(self, view, interaction):
        super().__init__(timeout=60)
        self.original_view = view
        self.original_interaction = interaction

    @discord.ui.button(label="Confirm Forfeit", style=discord.ButtonStyle.red, emoji="🏳️")
    async def async_confirm_forfeit(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Write forfeit to database
        # Disable buttons on this view
        async_tournament_race = await models.AsyncTournamentRace.get_or_none(thread_id=interaction.channel.id).prefetch_related('user')
        if async_tournament_race is None:
            await interaction.response.send_message("This race does not exist.  Please contact a moderator.", ephemeral=True)
            return

        if async_tournament_race.user.discord_user_id != interaction.user.id:
            await interaction.response.send_message("Only the runner may forfeit this race.", ephemeral=True)
            return

        if async_tournament_race.status not in ["pending", "in_progress"]:
            await interaction.response.send_message("The race must be pending or in progress to forfeit it.", ephemeral=True)
            return

        user, _ = await models.Users.get_or_create(discord_user_id=interaction.user.id)

        await models.AsyncTournamentAuditLog.create(
            tournament_id=async_tournament_race.tournament_id,
            user=user,
            action="runner_forfeit",
            details=f"{async_tournament_race.id} was forfeited by runner"
        )

        async_tournament_race.status = "forfeit"
        await async_tournament_race.save()
        await interaction.response.send_message(f"This run has been forfeited by {interaction.user.mention}.")
        for child_item in self.children:
            child_item.disabled = True
        await interaction.followup.edit_message(message_id=interaction.message.id, view=self)

        for child_item in self.original_view.children:
            child_item.disabled = True
        await self.original_interaction.followup.edit_message(message_id=self.original_interaction.message.id, view=self.original_view)


# button to open a modal to submit vod link and runner notes
class AsyncTournamentPostRaceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Submit VOD and Notes", style=discord.ButtonStyle.green, emoji="📹", custom_id="sahasrahbot:async_submit_vod")
    async def async_submit_vod(self, interaction: discord.Interaction, button: discord.ui.Button):
        race = await models.AsyncTournamentRace.get_or_none(thread_id=interaction.channel.id).prefetch_related('user')
        if race is None:
            await interaction.response.send_message("This is not a race thread.  This should not have happened.  Please contact a moderator.")
            return

        if race.user.discord_user_id != interaction.user.id:
            await interaction.response.send_message("Only the player may submit a VoD.", ephemeral=True)

        await interaction.response.send_modal(SubmitVODModal())


class SubmitVODModal(discord.ui.Modal, title="Submit VOD and Notes"):
    runner_vod_url = discord.ui.TextInput(label="VOD Link", placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ", row=0)
    runner_notes = discord.ui.TextInput(
        label="Runner Notes",
        placeholder="Any notes you want to leave for tournament admins regarding this run.",
        style=discord.TextStyle.long,
        required=False,
        row=1
    )

    async def on_submit(self, interaction: discord.Interaction):
        # write vod link and runner notes to database
        # close modal
        async_tournament_race = await models.AsyncTournamentRace.get_or_none(thread_id=interaction.channel.id)
        if async_tournament_race is None:
            await interaction.response.send_message("This race does not exist.  This should not have happened.  Please contact a moderator.")
            return

        async_tournament_race.runner_vod_url = self.runner_vod_url.value
        async_tournament_race.runner_notes = self.runner_notes.value
        await async_tournament_race.save()

        await interaction.response.send_message(f"VOD link and runner notes saved.\n\n**URL:**\n{self.runner_vod_url.value}\n\n**Notes:**\n{self.runner_notes.value}")


class AsyncTournament(commands.GroupCog, name="async"):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.timeout_warning_task.start()
        self.timeout_in_progress_races_task.start()
        self.persistent_views_added = False

    @tasks.loop(seconds=60, reconnect=True)
    async def timeout_warning_task(self):
        try:
            pending_races = await models.AsyncTournamentRace.filter(status="pending", thread_id__isnull=False).prefetch_related('user')
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
                    await thread.send(f"<@{pending_race.user.discord_user_id}>, your race will be permanently forfeit on {discord.utils.format_dt(forfeit_time, 'f')} ({discord.utils.format_dt(forfeit_time, 'R')}) if you do not start it by then.  Please start your run as soon as possible.  Please ping the @Admins if you require more time.", allowed_mentions=discord.AllowedMentions(users=True))

                if forfeit_time < discord.utils.utcnow():
                    await thread.send(f"<@{pending_race.user.discord_user_id}>, the grace period for the start of this run has elapsed.  This run has been forfeit.  Please contact the @Admins if you believe this was in error.", allowed_mentions=discord.AllowedMentions(users=True))
                    pending_race.status = "forfeit"
                    await pending_race.save()
                    await models.AsyncTournamentAuditLog.create(
                        tournament_id=pending_race.tournament_id,
                        action="timeout_forfeit",
                        details=f"{pending_race.id} was automatically forfeited by System due to timeout",
                    )
        except Exception:
            logging.exception("Exception in timeout_warning_task")

    @tasks.loop(seconds=60, reconnect=True)
    async def timeout_in_progress_races_task(self):
        try:
            races = await models.AsyncTournamentRace.filter(status="in_progress", thread_id__isnull=False).prefetch_related('user')
            for race in races:
                if race.start_time + datetime.timedelta(hours=12) > discord.utils.utcnow():
                    # this race is still in progress and has not timed out
                    continue

                thread = self.bot.get_channel(race.thread_id)
                if thread is None:
                    logging.warning("Cannot access thread for pending race %s.  This should not have happened.", race.id)
                    continue

                await thread.send(f"<@{race.user.discord_user_id}>, this race has exceeded 12 hours.  This run has been forfeit.  Please contact the @Admins if you believe this was in error.", allowed_mentions=discord.AllowedMentions(users=True))
                race.status = "forfeit"
                await race.save()
                await models.AsyncTournamentAuditLog.create(
                    tournament_id=race.tournament_id,
                    action="timeout_forfeit",
                    details=f"in progress race \"{race.id}\" was automatically forfeited by System due to timeout",
                )
        except Exception:
            logging.exception("Exception in timeout_in_progress_races_task")

    @timeout_warning_task.before_loop
    async def before_timeout_warning_task(self):
        await self.bot.wait_until_ready()

    @timeout_in_progress_races_task.before_loop
    async def before_timeout_in_progress_races_task(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.bot.add_view(AsyncTournamentView())
            self.bot.add_view(AsyncTournamentRaceViewReady())
            self.bot.add_view(AsyncTournamentRaceViewInProgress())
            self.bot.add_view(AsyncTournamentPostRaceView())
            self.persistent_views_added = True

    @app_commands.command(name="create", description="Create an async tournament")
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

        user, _ = await models.Users.get_or_create(discord_user_id=interaction.user.id)

        await models.AsyncTournamentAuditLog.create(
            tournament=async_tournament,
            user=user,
            action="create",
            details=f"{name} ({async_tournament.id}) created"
        )

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

    @app_commands.command(name="extendtimeout", description="Extend the timeout of this tournament run")
    async def extend_timeout(self, interaction: discord.Interaction, minutes: int):
        # TODO: replace this with a lookup on the config table for authorized users
        # if not await self.bot.is_owner(interaction.user):
        #     await interaction.response.send_message("Only Synack may create an async tournament at this time.", ephemeral=True)
        #     return

        async_tournament_race = await models.AsyncTournamentRace.get_or_none(thread_id=interaction.channel.id)
        if not async_tournament_race:
            await interaction.response.send_message("This channel is not an async tournament thread.", ephemeral=True)
            return

        if async_tournament_race.status != "pending":
            await interaction.response.send_message("This race is not pending.  It cannot be extended.", ephemeral=True)
            return

        await async_tournament_race.fetch_related("tournament")

        authorized = await async_tournament_race.tournament.permissions.filter(user__discord_user_id=interaction.user.id, role__in=['admin', 'mod'])
        if not authorized:
            await interaction.response.send_message("You are not authorized to extend the timeout for this tournament race.", ephemeral=True)
            return

        if async_tournament_race.thread_timeout_time is None:
            thread_timeout_time = async_tournament_race.thread_open_time + datetime.timedelta(minutes=20) + datetime.timedelta(minutes=minutes)
        else:
            thread_timeout_time = async_tournament_race.thread_timeout_time + datetime.timedelta(minutes=minutes)

        async_tournament_race.thread_timeout_time = thread_timeout_time
        await async_tournament_race.save()

        user, _ = await models.Users.get_or_create(discord_user_id=interaction.user.id)

        await models.AsyncTournamentAuditLog.create(
            tournament_id=async_tournament_race.tournament_id,
            user=user,
            action="extend_timeout",
            details=f"{async_tournament_race.id} extended by {minutes} minutes"
        )

        await interaction.response.send_message(f"Timeout extended to {discord.utils.format_dt(thread_timeout_time, 'f')} ({discord.utils.format_dt(thread_timeout_time, 'R')}).")

    @app_commands.command(name="repost", description="Repost the tournament embed")
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

    @app_commands.command(name="done", description="Finish the current race.")
    async def done(self, interaction: discord.Interaction):
        await finish_race(interaction)

    @app_commands.command(name="permissions", description="Configure permissions for this tournament")
    async def permissions(self, interaction: discord.Interaction, permission: str, role: discord.Role = None, user: discord.User = None):
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("Only Synack may create an async tournament at this time.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        async_tournament = await models.AsyncTournament.get_or_none(channel_id=interaction.channel.id)
        if async_tournament is None:
            await interaction.followup.send("This channel is not configured for async tournaments.  Please create a new tournament.", ephemeral=True)
            return

        if permission not in ["admin", "mod"]:
            await interaction.followup.send("Invalid permission.  Valid permissions are: admin, mod", ephemeral=True)
            return

        if role is None and user is None:
            await interaction.followup.send("Please specify a role or user.", ephemeral=True)
            return

        if role is not None and user is not None:
            await interaction.followup.send("Please specify a role OR a user, not both.", ephemeral=True)
            return

        if role is not None:
            if interaction.guild.chunked is False:
                await interaction.guild.chunk()

            for member in role.members:
                dbuser, _ = await models.Users.get_or_create(discord_user_id=member.id, defaults={"display_name": member.name})
                async_tournament_permission = await models.AsyncTournamentPermissions.get_or_none(
                    tournament=async_tournament,
                    user=dbuser,
                    role=permission
                )
                if async_tournament_permission is None:
                    await models.AsyncTournamentPermissions.create(
                        tournament=async_tournament,
                        user=dbuser,
                        role=permission
                    )
            await interaction.followup.send(f"Users in role {role.name} ({role.id}) has been granted {permission} permissions.", ephemeral=True)

        elif user is not None:
            dbuser, _ = await models.Users.get_or_create(discord_user_id=user.id, defaults={"display_name": user.name})
            async_tournament_permission = await models.AsyncTournamentPermissions.get_or_none(
                tournament=async_tournament,
                user=dbuser,
                role=permission
            )
            if async_tournament_permission is None:
                await models.AsyncTournamentPermissions.create(
                    tournament=async_tournament,
                    user=dbuser,
                    role=permission
                )

            await interaction.followup.send(f"{user.name} ({user.id}) has been granted {permission} permissions.", ephemeral=True)


def create_tournament_embed(async_tournament: models.AsyncTournament):
    embed = discord.Embed(title=async_tournament.name)
    embed.add_field(name="Owner", value=f"<@{async_tournament.owner_id}>", inline=False)
    embed.set_footer(text=f"ID: {async_tournament.id}")
    return embed

async def finish_race(interaction: discord.Interaction):
    race = await models.AsyncTournamentRace.get_or_none(thread_id=interaction.channel.id).prefetch_related('user')
    if race is None:
        await interaction.response.send_message("This channel/thread is not an async race room.", ephemeral=True)
        return

    if race.user.discord_user_id != interaction.user.id:
        await interaction.response.send_message("Only the player of this race may finish it.", ephemeral=True)
        return

    if race.status != "in_progress":
        await interaction.response.send_message("You may only finish a race that's in progress.", ephemeral=True)
        return

    user, _ = await models.Users.get_or_create(discord_user_id=interaction.user.id)

    await models.AsyncTournamentAuditLog.create(
        tournament_id=race.tournament_id,
        user=user,
        action="race_finish",
        details=f"{race.id} has finished"
    )

    race.end_time = discord.utils.utcnow()
    race.status = "finished"
    await race.save()

    elapsed = race.end_time - race.start_time

    await interaction.response.send_message(f"Your finish time of **{elapsed_time_hhmmss(elapsed)}** has been recorded.  Thank you for playing!\n\nDon't forget to submit a VoD of your run using the button below!", view=AsyncTournamentPostRaceView())


def elapsed_time_hhmmss(elapsed: datetime.timedelta):
    hours, remainder = divmod(elapsed.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

async def setup(bot: commands.Bot):
    await bot.add_cog(AsyncTournament(bot))
