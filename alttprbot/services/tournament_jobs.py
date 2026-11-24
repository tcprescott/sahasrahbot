"""Scheduled tournament jobs, driven by the SpeedGaming schedule.

These used to be ``discord.ext.tasks`` loops in ``alttprbot_discord/cogs/tournament.py``.
They do the work and publish events; Discord output is done by the subscribers in
``alttprbot_discord/notifications.py``.
"""
import datetime
import logging

from alttprbot import events, models, tournaments
from alttprbot.integrations import racetime
from alttprbot.services import bots, tournament_results
from alttprbot.tournament import core
from alttprbot.util import discord_members, speedgaming

logger = logging.getLogger(__name__)

# SpeedGaming channel ids that aren't real restream channels.
IGNORED_SG_CHANNEL_IDS = [0, 31, 36, 62, 63, 64, 65]
# Restream channels that need a broadcaster signed up.
BROADCASTER_CHANNELS = ['ALTTPRandomizer', 'ALTTPRandomizer2', 'ALTTPRandomizer3', 'ALTTPRandomizer4',
                        'ALTTPRandomizer5', 'ALTTPRandomizer6']


async def create_tournament_race_room(event, episodeid):
    """Open the racetime room for an episode, unless one is already open.

    A recorded room that was cancelled is forgotten and replaced.
    """
    event_data = await tournaments.TOURNAMENT_DATA[event].get_config()
    rtgg_bot = bots.racetime_bots()[event_data.data.racetime_category]
    race = await models.TournamentResults.get_or_none(episode_id=episodeid)
    if race:
        race_data = await racetime.get_race(race.srl_id, base_url=rtgg_bot.http_uri(""))
        status = race_data.get('status', {}).get('value')
        if not status == 'cancelled':
            return
        await race.delete()

    handler = await tournaments.TOURNAMENT_DATA[event].construct_race_room(episodeid)
    return handler


async def create_races() -> None:
    """Open racetime rooms for SpeedGaming episodes that are about to start."""
    logger.info("scanning SG schedule for tournament races to create")
    for event_slug, tournament_class in tournaments.TOURNAMENT_DATA.items():
        event_data: core.TournamentConfig = await tournament_class.get_config()
        try:
            episodes = await speedgaming.get_upcoming_episodes_by_event(
                event_slug, hours_past=0.5, hours_future=event_data.hours_before_room_open)
        except Exception:
            logger.exception("Encountered a problem when attempting to retrieve SG schedule.")
            continue
        for episode in episodes:
            logger.info(episode['id'])
            try:
                await create_tournament_race_room(event_slug, episode['id'])
            except Exception as e:
                logger.exception("Encountered a problem when attempting to create RT.gg race room.")
                events.publish(events.TournamentRoomCreationFailed(
                    event_slug=event_slug, episode_id=int(episode['id']), error=str(e)))
    logger.info('done')


async def week_races() -> None:
    """Submission reminders, Discord scheduled events and scheduling needs for the coming week."""
    logger.info('scanning for unsubmitted races')
    for event_slug, tournament_class in tournaments.TOURNAMENT_DATA.items():
        event_data: core.TournamentConfig = await tournament_class.get_config()

        try:
            episodes = await speedgaming.get_upcoming_episodes_by_event(event_slug, hours_past=0, hours_future=168)
        except Exception:
            logger.exception("Encountered a problem when attempting to retrieve SG schedule.")
            continue

        if event_data.submission_form:
            for episode in episodes:
                await send_race_form(event_slug, episode)

        if event_data.data.create_scheduled_events:
            events.publish(events.TournamentEpisodesRefreshed(event_slug=event_slug, episodes=tuple(episodes)))

        if event_data.data.scheduling_needs_channel:
            events.publish(scheduling_needs(
                event_slug, episodes, lang=event_data.lang,
                include_trackers=event_data.data.scheduling_needs_tracker))


async def send_race_form(event_slug: str, episode: dict) -> None:
    try:
        tournament_race = await tournaments.fetch_tournament_handler(event_slug, episode['id'])
        await tournament_race.send_race_submission_form()
    except Exception as e:
        logger.exception("Encountered a problem when attempting send race submission.")
        events.publish(events.RaceSubmissionReminderFailed(
            event_slug=event_slug, episode_id=int(episode['id']), error=str(e)))


def scheduling_needs(event_slug: str, episodes: list[dict], lang: str = 'en',
                     include_trackers: bool = True) -> events.SchedulingNeedsUpdated:
    """Work out which restreamed episodes still need commentators, trackers or broadcasters."""
    comms_needed = []
    trackers_needed = []
    broadcasters_needed = []

    for episode in episodes:
        broadcast_channels = [c['slug'] for c in episode['channels'] if
                              c['id'] not in IGNORED_SG_CHANNEL_IDS and c['language'] == lang]
        if not broadcast_channels:
            continue

        start_time = datetime.datetime.strptime(episode['when'], "%Y-%m-%dT%H:%M:%S%z")

        commentators_approved = [p for p in episode['commentators'] if p['approved'] and p['language'] == lang]
        if (c_needed := 2 - len(commentators_approved)) > 0:
            comms_needed.append(events.StaffNeed(
                start_time, c_needed, f"https://speedgaming.org/commentator/signup/{episode['id']}/"))

        if include_trackers:
            trackers_approved = [p for p in episode['trackers'] if p['approved'] and p['language'] == lang]
            t_needed = (2 if len(episode['match1']['players']) > 2 else 1) - len(trackers_approved)
            if t_needed > 0:
                trackers_needed.append(events.StaffNeed(
                    start_time, t_needed, f"https://speedgaming.org/tracker/signup/{episode['id']}/"))

        if broadcast_channels[0] in BROADCASTER_CHANNELS:
            broadcasters_approved = [p for p in episode['broadcasters'] if p['approved'] and p['language'] == lang]
            if (b_needed := 1 - len(broadcasters_approved)) > 0:
                broadcasters_needed.append(events.StaffNeed(
                    start_time, b_needed, f"https://speedgaming.org/broadcaster/signup/{episode['id']}/"))

    return events.SchedulingNeedsUpdated(
        event_slug=event_slug,
        commentators=tuple(comms_needed),
        trackers=tuple(trackers_needed),
        broadcasters=tuple(broadcasters_needed),
    )


async def record_races() -> None:
    """Write finished tournament results to the events' Google Sheets."""
    logger.info("recording tournament races")
    await tournament_results.record_results()
    logger.info("done recording")


async def find_races_with_bad_discord() -> None:
    """Report SpeedGaming players in the next 48 hours who aren't in the event's guild."""
    logger.info('scanning for races with bad discord info')
    for event_slug in tournaments.TOURNAMENT_DATA:
        try:
            messages = await report_bad_player_discord(event_slug)
        except Exception:
            logger.exception("Unable to check player Discord info for %s", event_slug)
            continue
        if messages:
            events.publish(events.UnmatchedPlayersFound(event_slug=event_slug, messages=tuple(messages)))


async def report_bad_player_discord(event_slug: str) -> list[str]:
    tournament_class = tournaments.TOURNAMENT_DATA[event_slug]

    event_data: core.TournamentConfig = await tournament_class.get_config()
    episodes = await speedgaming.get_upcoming_episodes_by_event(event_slug, hours_past=0, hours_future=48)

    messages = []

    for episode in episodes:
        for match in ['match1', 'match2']:
            if episode[match]:
                for player in episode[match]['players']:
                    if player['publicStream'] == 'ignore':
                        continue

                    if player['displayName'].startswith('Winner of '):
                        continue

                    if player['displayName'].startswith('Loser of '):
                        continue

                    try:
                        member = await discord_members.get_member(event_data.guild, int(player.get('discordId', '')))
                    except ValueError:
                        member = None

                    if member is None:
                        discord_name: str = player.get('discordTag', '')
                        if discord_name.endswith('#0'):  # strip the #0 off the end of the name
                            discord_name = discord_name[:-2]
                        member = await discord_members.get_member_named(event_data.guild, discord_name)

                    if member is None:
                        messages.append(
                            f"Episode {episode['id']} - {event_slug} - {player['displayName']} could not be found")

    return messages
