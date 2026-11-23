"""Discord output for the scheduled jobs' events.

The jobs in ``alttprbot/services/`` (registered in ``alttprbot/services/scheduled_jobs.py``)
publish events; these subscribers turn them into Discord messages, scheduled events
and embeds. ``register(bot)`` is called from ``sahasrahbot.py`` before the bots start.

Every handler waits for the bot to be ready (``wait_until_ready``), so an event published while Discord is
still connecting is delivered once it's up rather than dropped.
"""
import asyncio
import datetime
import logging

import discord
from discord.ext import commands

from alttprbot import models, tournaments
from alttprbot.services import guild_config, job_events as events
from alttprbot.tournament import core

logger = logging.getLogger(__name__)

DAILY_NOTES = "This is today's daily challenge.  The latest challenge can always be found at https://alttpr.com/daily"
BAD_DISCORD_REPORT_MENTION = "<@185198185990324225>"


async def wait_until_ready(bot: commands.Bot) -> None:
    """Wait for the bot to be ready.

    Unlike ``bot.wait_until_ready()``, this is safe to call before the bot has started
    logging in, which a scheduled job or an early event can do.
    """
    while not bot.is_ready():
        await asyncio.sleep(1)


def register(bot: commands.Bot) -> list:
    """Subscribe the Discord handlers. Returns the subscription tokens."""
    output = ScheduledJobDiscordOutput(bot)
    return [
        events.subscribe(events.DailyChallengeAvailable, output.announce_daily),
        events.subscribe(events.TournamentRoomCreationFailed, output.report_room_creation_failed),
        events.subscribe(events.RaceSubmissionReminderFailed, output.report_submission_reminder_failed),
        events.subscribe(events.TournamentEpisodesRefreshed, output.update_scheduled_events),
        events.subscribe(events.SchedulingNeedsUpdated, output.update_scheduling_needs),
        events.subscribe(events.UnmatchedPlayersFound, output.report_unmatched_players),
    ]


def _format_needs(needs) -> list[str]:
    return [f"*{discord.utils.format_dt(n.start_time, 'f')}* - Need **{n.count}** - [Sign Up!]({n.signup_url})"
            for n in needs]


def build_scheduling_needs_embed(needs: events.SchedulingNeedsUpdated, include_trackers: bool) -> discord.Embed:
    comms_needed = _format_needs(needs.commentators)
    trackers_needed = _format_needs(needs.trackers)
    broadcasters_needed = _format_needs(needs.broadcasters)

    embed = discord.Embed(
        title="Scheduling Needs",
        description="This is the current scheduling needs for the next 48 hours.\n\nTimes are shown in your **local time zone**.",
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(
        name="Commentators Needed",
        value="\n".join(comms_needed) if comms_needed else "No current needs.",
        inline=False
    )
    if include_trackers:
        embed.add_field(
            name="Trackers Needed",
            value="\n".join(trackers_needed) if trackers_needed else "No current needs.",
            inline=False
        )
    if broadcasters_needed:
        embed.add_field(
            name="Broadcasters Needed",
            value="\n".join(broadcasters_needed),
            inline=False
        )
    return embed


class ScheduledJobDiscordOutput:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _event_config(self, event_slug: str) -> core.TournamentConfig:
        await wait_until_ready(self.bot)
        return await tournaments.TOURNAMENT_DATA[event_slug].get_config()

    async def announce_daily(self, event: events.DailyChallengeAvailable):
        # Imported here: the cog module owns the seed lookup and its cache.
        from alttprbot_discord.cogs.daily import get_daily_seed

        await wait_until_ready(self.bot)
        seed = await get_daily_seed(event.hash_id)
        embed = await seed.embed(emojis=self.bot.emojis, notes=DAILY_NOTES)
        daily_announcer_channels = await guild_config.guilds_with('DailyAnnouncerChannel')
        for guild_id, value in daily_announcer_channels.items():
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                logger.warning("Daily announcer guild %s is not available.", guild_id)
                continue
            for channel_name in (value or "").split(","):
                channel = discord.utils.get(guild.text_channels, name=channel_name)
                if channel is None:
                    logger.warning("Daily announcer channel %s not found in guild %s.", channel_name, guild.id)
                    continue
                try:
                    message: discord.Message = await channel.send(embed=embed)
                    await message.create_thread(name=seed.data['spoiler']['meta'].get('name'),
                                                auto_archive_duration=1440)
                except Exception:
                    logger.exception("Unable to announce the daily in %s/%s.", guild.id, channel_name)

    async def report_room_creation_failed(self, event: events.TournamentRoomCreationFailed):
        event_data = await self._event_config(event.event_slug)
        if event_data.audit_channel:
            await event_data.audit_channel.send(
                f"There was an error while automatically creating a race room for episode `{event.episode_id}`.\n\n{event.error}",
                allowed_mentions=discord.AllowedMentions(everyone=True)
            )

    async def report_submission_reminder_failed(self, event: events.RaceSubmissionReminderFailed):
        event_data = await self._event_config(event.event_slug)
        if event_data.audit_channel:
            await event_data.audit_channel.send(
                f"There was an error while sending a submission reminder for episode `{event.episode_id}`.\n\n{event.error}",
                allowed_mentions=discord.AllowedMentions(everyone=True)
            )

    async def report_unmatched_players(self, event: events.UnmatchedPlayersFound):
        event_data = await self._event_config(event.event_slug)
        if event_data.audit_channel:
            await event_data.audit_channel.send(f"{BAD_DISCORD_REPORT_MENTION}\n\n" + "\n".join(event.messages))

    async def update_scheduling_needs(self, event: events.SchedulingNeedsUpdated):
        event_data = await self._event_config(event.event_slug)
        channel = event_data.data.scheduling_needs_channel
        if channel is None:
            return
        embed = build_scheduling_needs_embed(event, include_trackers=event_data.data.scheduling_needs_tracker)

        try:
            async for message in channel.history(limit=50):
                if message.author == self.bot.user:
                    await message.edit(embed=embed)
                    break
            else:
                await channel.send(embed=embed)
        except Exception:
            logger.exception("Unable to update scheduling needs channel.")

    async def update_scheduled_events(self, event: events.TournamentEpisodesRefreshed):
        """Mirror the event's SpeedGaming episodes as Discord guild scheduled events."""
        event_data = await self._event_config(event.event_slug)
        event_slug = event.event_slug
        episodes = list(event.episodes)

        # remove dead events
        dead_events = await models.ScheduledEvents.filter(episode_id__not_in=[e['id'] for e in episodes],
                                                          event_slug=event_slug)
        for dead_event in dead_events:
            try:
                guild_event: discord.ScheduledEvent = await event_data.guild.fetch_scheduled_event(
                    dead_event.scheduled_event_id)

                if guild_event.status == discord.EventStatus.scheduled:
                    await guild_event.delete()
            except discord.NotFound:
                continue
            await dead_event.delete()

        for episode in episodes:
            start_time = datetime.datetime.strptime(episode['when'], "%Y-%m-%dT%H:%M:%S%z")
            episode_id = int(episode['id'])
            scheduled_event = await models.ScheduledEvents.get_or_none(episode_id=episode_id)

            try:
                tournament_race = await tournaments.fetch_tournament_handler_v2(event_slug, episode)
            except Exception:
                logger.exception("Error while creating tournament race handler.")
                continue

            name = tournament_race.event_slug.upper()
            if tournament_race.friendly_name:
                name += f" - {tournament_race.friendly_name}"
            if tournament_race.versus:
                name += f" - {tournament_race.versus}"

            name = name[:100]

            description = f"Start Time: {discord.utils.format_dt(start_time, 'f')}"
            end_time = start_time + datetime.timedelta(hours=2)

            if tournament_race.broadcast_channels:
                location = f"https://twitch.tv/{tournament_race.broadcast_channels[0]}"
            elif tournament_race.player_twitch_names:
                location = f"https://multistre.am/{'/'.join(tournament_race.player_twitch_names)}/layout3/"
            else:
                location = "TBD"

            try:
                if scheduled_event:
                    try:
                        guild_event: discord.ScheduledEvent = await event_data.guild.fetch_scheduled_event(
                            scheduled_event.scheduled_event_id)

                        # check if existing event requires an update
                        if not guild_event.name == name or not guild_event.description == description or not guild_event.start_time == start_time or not guild_event.end_time == end_time or not guild_event.location == location:
                            await guild_event.edit(
                                name=name,
                                description=description,
                                start_time=start_time,
                                end_time=end_time,
                                location=location,
                                entity_type=discord.EntityType.external,
                                privacy_level=discord.PrivacyLevel.guild_only
                            )
                    except discord.NotFound:
                        guild_event = await event_data.guild.create_scheduled_event(
                            name=name,
                            description=description,
                            start_time=start_time,
                            end_time=end_time,
                            location=location,
                            entity_type=discord.EntityType.external,
                            privacy_level=discord.PrivacyLevel.guild_only
                        )
                        await models.ScheduledEvents.update_or_create(episode_id=episode_id,
                                                                      defaults={'scheduled_event_id': guild_event.id,
                                                                                'event_slug': event_slug})
                else:
                    # create an event
                    guild_event = await event_data.guild.create_scheduled_event(
                        name=name,
                        description=description,
                        start_time=start_time,
                        end_time=end_time,
                        location=location,
                        entity_type=discord.EntityType.external,
                        privacy_level=discord.PrivacyLevel.guild_only
                    )
                    await models.ScheduledEvents.create(scheduled_event_id=guild_event.id, episode_id=episode_id,
                                                        event_slug=event_slug)
            except Exception:
                logger.exception("Unable to create guild event.")

