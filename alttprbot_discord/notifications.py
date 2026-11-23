"""Discord subscribers for the event bridge (``alttprbot/events``).

Services publish what happened; this module decides what Discord sees. Each
handler waits for the bot to be ready, looks up its channels and users by id,
and posts. ``register(bot)`` is called once from ``sahasrahbot.py``.

Add a handler here when an event should reach Discord, and subscribe it in
``register``. A handler's exception is logged by the bus and never reaches the
publisher.
"""

import json
import logging

import aiohttp
import discord
from discord.ext import commands

import config
from alttprbot import events, models
from alttprbot.util import rankedchoice

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


class DiscordNotifier:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _user(self, user_id: int):
        return self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)

    # --- tournament and daily race rooms -------------------------------------

    async def on_tournament_room_opened(self, event: events.TournamentRoomOpened):
        await self.bot.wait_until_ready()

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
        await self.bot.wait_until_ready()
        await self._watchlisted_players(event)
        await self._new_players(event)

    async def _racetime_user(self, event: events.RaceStatusChanged, racetime_id: str) -> dict:
        async with aiohttp.request(method='get', url=f"{event.base_url}/user/{racetime_id}/data",
                                   raise_for_status=True) as resp:
            return json.loads(await resp.read())

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
        await self.bot.wait_until_ready()
        election = await models.RankedChoiceElection.get_or_none(id=event.election_id)
        if election is None:
            return
        await rankedchoice.refresh_election_post(election, self.bot)


_tokens: list[int] = []


def register(bot: commands.Bot) -> DiscordNotifier:
    """Subscribe the Discord handlers. Calling it again replaces the earlier set."""
    unregister()
    notifier = DiscordNotifier(bot)
    _tokens.extend([
        events.subscribe(events.TournamentRoomOpened, notifier.on_tournament_room_opened),
        events.subscribe(events.RaceStatusChanged, notifier.on_race_status_changed),
        events.subscribe(events.RankedChoiceBallotCast, notifier.on_ranked_choice_ballot_cast),
    ])
    return notifier


def unregister() -> None:
    while _tokens:
        events.unsubscribe(_tokens.pop())
