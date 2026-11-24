"""Discord subscribers for the event bridge (``alttprbot/events``).

Services and the scheduled jobs (``alttprbot/services/scheduled_jobs.py``)
publish what happened; this module decides what Discord sees. Each handler
waits for the bot to be ready (``wait_until_ready``, safe before the bot has
started logging in, so an early event is delivered once Discord is up rather
than dropped), looks up its channels and users by id, and posts.
``register(bot)`` is called once from ``sahasrahbot.py``.

Add a handler here when an event should reach Discord, and subscribe it in
``register``. A handler's exception is logged by the bus and never reaches the
publisher.
"""

import asyncio
import datetime
import logging

import aiohttp
import discord
from discord.ext import commands

import config
from alttprbot import events, models, tournaments
from alttprbot.integrations import racetime
from alttprbot.services import guild_config
from alttprbot.tournament import core
from alttprbot.util import rankedchoice
from alttprbot_discord.util.seed_embeds import seed_embed

logger = logging.getLogger(__name__)

# Open races that announce in a channel when their room opens, by SG event slug.
# The SpeedGaming daily (and its webhook) shows when the seed is distributed.
DAILY_ANNOUNCEMENTS = {
    'alttprdaily': {
        'channel_id': 307861467838021633,
        'heading': "SpeedGaming Daily Race Series",
        'mention': None,
        'webhook_mention': "<@&399038388964950016>",
        'show_seed_time': True,
    },
    'smz3': {
        'channel_id': 451977523123978260,
        'heading': "SMZ3 Weekly Race",
        'mention': "<@&449260882501959700>",
        'webhook_mention': None,
        'show_seed_time': False,
    },
}


def daily_announcement(event: events.TournamentRoomOpened, settings: dict) -> str:
    """The channel text for an open race's room, as the dailies have always posted it."""
    msg = "{heading} - {title} - {start_time} ({start_time_remain})".format(
        heading=settings['heading'],
        title=event.title,
        start_time=discord.utils.format_dt(event.start_time),
        start_time_remain=discord.utils.format_dt(event.start_time, "R"),
    )
    if settings['mention']:
        msg = f"{settings['mention']} {msg}"

    if event.broadcast_channels:
        msg += f" on {', '.join(event.broadcast_channels)}"

    if settings['show_seed_time'] and event.seed_time:
        msg += f" - Seed Distributed {discord.utils.format_dt(event.seed_time, 'R')}"

    msg += f" - {event.room_url}"
    return msg


def room_opened_embed(event: events.TournamentRoomOpened) -> discord.Embed:
    return discord.Embed(
        title=f"RT.gg Room Opened - {event.versus}",
        description=(
            "Greetings!  A RaceTime.gg race room has been automatically opened for you.\n"
            f"You may access it at {event.room_url}\n\nEnjoy!"
        ),
        color=discord.Colour.blue(),
        timestamp=discord.utils.utcnow(),
    )


# --- scheduled jobs ------------------------------------------------------------

DAILY_NOTES = "This is today's daily challenge.  The latest challenge can always be found at https://alttpr.com/daily"
BAD_DISCORD_REPORT_MENTION = "<@185198185990324225>"


def _embed(data):
    """Rebuild an embed the engine sent as ``discord.Embed.to_dict()``."""
    return discord.Embed.from_dict(data) if data else None


async def wait_until_ready(bot: commands.Bot) -> None:
    """Wait for the bot to be ready.

    Unlike ``bot.wait_until_ready()``, this is safe to call before the bot has started
    logging in, which a scheduled job or an early event can do.
    """
    while not bot.is_ready():
        await asyncio.sleep(1)


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
        embed = await seed_embed(seed, emojis=self.bot.emojis, notes=DAILY_NOTES)
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


# --- everything else ------------------------------------------------------------

class DiscordNotifier:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _user(self, user_id: int):
        return self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)

    # --- tournament and daily race rooms -------------------------------------

    async def on_tournament_room_opened(self, event: events.TournamentRoomOpened):
        await wait_until_ready(self.bot)

        settings = DAILY_ANNOUNCEMENTS.get(event.event_slug)
        if settings:
            await self._announce_daily(event, settings)

        if not event.player_discord_ids:
            return
        embed = room_opened_embed(event)
        for user_id in event.player_discord_ids:
            try:
                user = await self._user(user_id)
                await user.send(embed=embed)
            except discord.HTTPException:
                logger.info("Could not send room opening DM to %s for episode %s", user_id, event.episode_id)

    def _channel(self, channel_id: int, event) -> discord.abc.Messageable:
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            logger.warning("Channel %s for %s (episode %s) is not available.", channel_id, event.name, event.episode_id)
        return channel

    async def on_tournament_audit_recorded(self, event: events.TournamentAuditRecorded):
        await wait_until_ready(self.bot)
        channel = self._channel(event.channel_id, event)
        if channel is None:
            return
        await channel.send(content=event.content, embed=_embed(event.embed))

    async def on_tournament_commentary_ready(self, event: events.TournamentCommentaryReady):
        await wait_until_ready(self.bot)
        channel = self._channel(event.channel_id, event)
        if channel is None:
            return
        await channel.send(embed=_embed(event.embed))

    async def on_tournament_settings_submitted(self, event: events.TournamentSettingsSubmitted):
        await wait_until_ready(self.bot)
        embed = _embed(event.embed)
        audit_channel = None
        if event.audit_channel_id is not None:
            audit_channel = self._channel(event.audit_channel_id, event)
        if audit_channel:
            await audit_channel.send(embed=embed)

        for player in event.players:
            await self._dm_settings(player, embed, audit_channel)

    async def _dm_settings(self, player: events.TournamentPlayerRef, embed, audit_channel):
        here = discord.AllowedMentions(everyone=True)
        if player.discord_id is None:
            logger.error("Could not send DM to %s", player.name)
            if audit_channel:
                await audit_channel.send(f"@here could not send DM to {player.name}", allowed_mentions=here, embed=embed)
            return
        user = None
        try:
            user = await self._user(player.discord_id)
            await user.send(embed=embed)
        except discord.HTTPException:
            logger.exception("Could not send DM to %s", player.name)
            if audit_channel:
                who = f"{user.name}#{user.discriminator}" if user else player.name
                await audit_channel.send(f"@here could not send DM to {who}", allowed_mentions=here, embed=embed)

    async def _announce_daily(self, event: events.TournamentRoomOpened, settings: dict):
        message = daily_announcement(event, settings)
        channel = self.bot.get_channel(settings['channel_id'])
        if channel is None:
            logger.warning("Announcement channel %s for %s not found", settings['channel_id'], event.event_slug)
        else:
            await channel.send(content=message, allowed_mentions=discord.AllowedMentions(roles=True))

        if settings['webhook_mention'] and config.SG_DISCORD_WEBHOOK:
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(config.SG_DISCORD_WEBHOOK, session=session)
                await webhook.send(f"{settings['webhook_mention']} {message}", username="SahasrahBot")

    # --- racetime.gg rooms ----------------------------------------------------

    async def on_race_status_changed(self, event: events.RaceStatusChanged):
        if event.status != 'in_progress':
            return
        await wait_until_ready(self.bot)
        await self._watchlisted_players(event)
        await self._new_players(event)

    async def _racetime_user(self, event: events.RaceStatusChanged, racetime_id: str) -> dict:
        return await racetime.get_user(racetime_id, base_url=event.base_url)

    async def _watchlisted_players(self, event: events.RaceStatusChanged):
        watchlisted_players = await models.RTGGWatcherPlayer.filter(
            racetime_id__in=list(event.entrant_ids),
            rtgg_watcher__category=event.category,
        ).prefetch_related("rtgg_watcher")
        for watchlisted_player in watchlisted_players:
            channel = self.bot.get_channel(watchlisted_player.rtgg_watcher.channel_id)
            user_data = await self._racetime_user(event, watchlisted_player.racetime_id)
            player_profile_uri = f"{event.base_url}{user_data['url']}"

            embed = discord.Embed(
                title="Watchlisted Player Detected in race",
                description=f"Watchlisted player [{user_data['full_name']}]({player_profile_uri}) began racing in [{event.room_name}]({event.room_url})",
                color=discord.Colour.red()
            )
            await channel.send(embed=embed)

    async def _new_players(self, event: events.RaceStatusChanged):
        watchers = await models.RTGGWatcher.filter(category=event.category, notify_on_new_player=True)
        if not watchers:
            return

        new_players = []
        for entrant in event.entrant_ids:
            user_data = await self._racetime_user(event, entrant)
            if user_data['stats']['joined'] == 0:
                new_players.append(user_data)

        for watcher in watchers:
            channel = self.bot.get_channel(watcher.channel_id)
            for user_data in new_players:
                player_profile_uri = f"{event.base_url}{user_data['url']}"
                embed = discord.Embed(
                    title="New Racer Detected!",
                    description=f"A new racer named [{user_data['full_name']}]({player_profile_uri}) began racing in [{event.room_name}]({event.room_url})",
                    color=discord.Colour.green()
                )
                await channel.send(embed=embed)

    # --- ranked choice elections ----------------------------------------------

    async def on_ranked_choice_ballot_cast(self, event: events.RankedChoiceBallotCast):
        await wait_until_ready(self.bot)
        election = await models.RankedChoiceElection.get_or_none(id=event.election_id)
        if election is None:
            return
        await rankedchoice.refresh_election_post(election, self.bot)


_tokens: list[int] = []


def register(bot: commands.Bot) -> DiscordNotifier:
    """Subscribe the Discord handlers. Calling it again replaces the earlier set."""
    unregister()
    notifier = DiscordNotifier(bot)
    jobs = ScheduledJobDiscordOutput(bot)
    _tokens.extend([
        events.subscribe(events.TournamentRoomOpened, notifier.on_tournament_room_opened),
        events.subscribe(events.TournamentAuditRecorded, notifier.on_tournament_audit_recorded),
        events.subscribe(events.TournamentCommentaryReady, notifier.on_tournament_commentary_ready),
        events.subscribe(events.TournamentSettingsSubmitted, notifier.on_tournament_settings_submitted),
        events.subscribe(events.RaceStatusChanged, notifier.on_race_status_changed),
        events.subscribe(events.RankedChoiceBallotCast, notifier.on_ranked_choice_ballot_cast),
        events.subscribe(events.DailyChallengeAvailable, jobs.announce_daily),
        events.subscribe(events.TournamentRoomCreationFailed, jobs.report_room_creation_failed),
        events.subscribe(events.RaceSubmissionReminderFailed, jobs.report_submission_reminder_failed),
        events.subscribe(events.TournamentEpisodesRefreshed, jobs.update_scheduled_events),
        events.subscribe(events.SchedulingNeedsUpdated, jobs.update_scheduling_needs),
        events.subscribe(events.UnmatchedPlayersFound, jobs.report_unmatched_players),
    ])
    return notifier


def unregister() -> None:
    while _tokens:
        events.unsubscribe(_tokens.pop())
