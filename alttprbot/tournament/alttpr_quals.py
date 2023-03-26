import discord
import datetime
import pytz
import isodate

from alttprbot import models
from alttprbot.tournament.core import TournamentRace, TournamentConfig
from alttprbot_discord.bot import discordbot
from alttprbot.util import speedgaming, triforce_text
from alttprbot_racetime import bot as racetime
from alttprbot_racetime.core import SahasrahBotRaceTimeBot


class ALTTPRQualifierRace(TournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(334795604918272012)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game',
            event_slug="alttpr",
            audit_channel=discordbot.get_channel(647966639266201620),
            commentary_channel=discordbot.get_channel(947095820673638400),
            scheduling_needs_channel=discordbot.get_channel(434560353461075969),
            scheduling_needs_tracker=True,
            create_scheduled_events=True,
            stream_delay=10,
            room_open_time=60,
            helper_roles=[
                guild.get_role(334797023054397450),
                guild.get_role(435200206552694794),
                guild.get_role(482353483853332481),
                guild.get_role(426487540829388805),
                guild.get_role(613394561594687499),
                guild.get_role(334796844750209024)
            ]
        )

    # When !tournamentrace is called, this is the first function that is called
    # 1. Let runner of command know that stuff is happening
    # 2. Roll the seed
    # 3. Send the seed to the racetime room
    # 5. Send the seed to the audit channel
    # 4. Write the seed to models.AsyncTournamentPermalink
    # 5. Write to models.AsyncTournamentRace records for each runner who's run will count.
    #   a. Write this list to the audit channel.
    #   b. Create Users if they don't exist.
    async def process_tournament_race(self, args, message):
        await self.rtgg_handler.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")
        await self.update_data()

        async_tournament_live_race = await models.AsyncTournamentLiveRace.get_or_none(
            episode_id=self.episodeid,
        ).prefetch_related('pool', 'permalink')

        # a whole bunch of guard conditions we need to satisfy before we can roll a seed
        if async_tournament_live_race is None:
            await self.rtgg_handler.send_message("No live race found for this episode.  Please contact Synack for further help.")
            return

        if async_tournament_live_race.permalink is not None:
            await self.rtgg_handler.send_message("Seed has already been generated for this live race.  Please contact Synack for further help.")
            return

        if async_tournament_live_race.pool is None:
            await self.rtgg_handler.send_message("No pool has been set for this live race.  Please contact Synack for further help.")
            return

        await async_tournament_live_race.fetch_related('tournament')

        authorized = await models.AsyncTournamentPermissions.filter(
            tournament=async_tournament_live_race.tournament,
            user__rtgg_id=message['user']['id'],
            role__in=['mod', 'admin']
        )
        if not authorized:
            await self.rtgg_handler.send_message("Only a mod or admin of this tournament may invoke !tournamentrace.  Please contact Synack for further help.")
            return

        await async_tournament_live_race.fetch_related('pool')

        if async_tournament_live_race.pool.preset is None:
            await self.rtgg_handler.send_message("No preset has been set for this pool.  Please contact Synack for further help.")
            return

        # lock the room
        await self.rtgg_handler.set_invitational()
        await self.rtgg_handler.edit(streaming_required=False)
        await self.rtgg_handler.send_message("This room is now locked.  Please contact a Tournament Moderator if you need to be added to the room.")

        preset = async_tournament_live_race.pool.preset

        self.seed = await triforce_text.generate_with_triforce_text("alttpr2023", preset)

        await self.rtgg_handler.set_bot_raceinfo(f"{self.seed.url} - {self.seed_code}")
        await self.send_audit_message(f"{self.rtgg_bot.http_uri(self.rtgg_handler.data['url'])} - {self.seed.url} - {self.seed_code}")

        tournamentresults, _ = await models.TournamentResults.update_or_create(srl_id=self.rtgg_handler.data.get('name'), defaults={'episode_id': self.episodeid, 'event': self.event_slug, 'spoiler': None})
        tournamentresults.permalink = self.seed.url
        await tournamentresults.save()

        async_tournament_permalink = await models.AsyncTournamentPermalink.create(
            url=self.seed.url,
            pool=async_tournament_live_race.pool,
            notes=f"Generated for a live race.  {self.seed_code}",
            live_race=True
        )

        async_tournament_live_race.permalink = async_tournament_permalink
        async_tournament_live_race.racetime_slug = self.rtgg_handler.data.get('name')
        await async_tournament_live_race.save()

        eligible_entrants_for_pool = await write_eligible_async_entrants(
            async_tournament_live_race=async_tournament_live_race,
            permalink=async_tournament_permalink,
            race_room_data=self.rtgg_handler.data
        )

        # TODO: RT.gg max message length is 1000 characters, we need to split this up if we have more than 1000 characters
        await self.rtgg_handler.send_message(f"Eligible entrants for this pool: {', '.join(eligible_entrants_for_pool)}")
        await self.send_audit_message(f"{self.rtgg_bot.http_uri(self.rtgg_handler.data['url'])} -Eligible entrants for this pool: {', '.join(eligible_entrants_for_pool)}")
        self.rtgg_handler.seed_rolled = True

    async def on_race_start(self):
        async_tournament_live_race = await models.AsyncTournamentLiveRace.get_or_none(
            episode_id=self.episodeid,
        )
        # entrants = self.rtgg_handler.data.get('entrants', [])
        in_progress_entrants = await process_async_tournament_start(
            async_tournament_live_race=async_tournament_live_race,
            race_room_data=self.rtgg_handler.data
        )

        await self.send_audit_message(f"{self.rtgg_bot.http_uri(self.rtgg_handler.data['url'])} - Entrants: {', '.join(in_progress_entrants)}")
        await self.rtgg_handler.send_message(f"Final eligible entrants for this pool: {', '.join(in_progress_entrants)}")
        await self.rtgg_handler.send_message("Good luck, have fun!  Mid-race chat is disabled.  If you need assistance, please ping @Admins in Discord.")

    @property
    def seed_code(self):
        return f"({'/'.join(self.seed.code)})"

    @property
    def announce_channel(self):
        return discordbot.get_channel(407803705375850506)

    @property
    def announce_message(self):
        msg = "ALTTPR Main Tournament Live Qualifier - {title} - {start_time} ({start_time_remain})".format(
            title=self.friendly_name,
            start_time=discord.utils.format_dt(self.race_start_time),
            start_time_remain=discord.utils.format_dt(self.race_start_time, "R")
        )

        if self.broadcast_channels:
            msg += f" on {', '.join(self.broadcast_channels)}"

        msg += " - Seed Distributed {seed_time} - {racetime_url}".format(
            seed_time=discord.utils.format_dt(self.seed_time, "R"),
            racetime_url=self.rtgg_bot.http_uri(self.rtgg_handler.data['url'])
        )
        return msg

    @property
    def race_info(self):
        msg = "ALTTPR Main Tournament Live Qualifier - {title} at {start_time} Eastern".format(
            title=self.friendly_name,
            start_time=self.string_time(self.race_start_time)
        )

        if self.broadcast_channels:
            msg += f" on {', '.join(self.broadcast_channels)}"

        msg += " - Seed Distributed at {seed_time} Eastern".format(
            seed_time=self.string_time(self.seed_time),
        )
        msg += f" - {self.episodeid}"
        return msg

    async def create_race_room(self):
        self.rtgg_handler = await self.rtgg_bot.startrace(
            goal=self.data.racetime_goal,
            invitational=False,
            unlisted=False,
            info_user=self.race_info,
            start_delay=15,
            time_limit=24,
            streaming_required=True,
            auto_start=False,
            allow_comments=True,
            hide_comments=True,
            allow_prerace_chat=False,
            allow_midrace_chat=False,
            allow_non_entrant_chat=False,
            chat_message_delay=0,
            team_race=False,
        )
        return self.rtgg_handler

    @property
    def player_racetime_ids(self):
        return []

    @property
    def seed_time(self):
        return self.race_start_time - datetime.timedelta(minutes=10)

    async def send_player_room_info(self):
        await self.announce_channel.send(
            content=self.announce_message,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )

    async def update_data(self, update_episode=True):
        if update_episode:
            self.episode = await speedgaming.get_episode(self.episodeid)

        self.tournament_game = await models.TournamentGames.get_or_none(episode_id=self.episodeid)

        self.rtgg_bot: SahasrahBotRaceTimeBot = racetime.racetime_bots[self.data.racetime_category]
        self.restream_team = await self.rtgg_bot.get_team('sg-volunteers')


async def write_eligible_async_entrants(async_tournament_live_race: models.AsyncTournamentLiveRace, permalink: models.AsyncTournamentPermalink, race_room_data: dict):
    entrants = race_room_data.get('entrants', [])

    eligible_entrants_for_pool = []

    # iterate through entrants and create a AsyncTournamentRace record for each one
    for entrant in entrants:
        user, new = await models.Users.get_or_create(
            rtgg_id=entrant['user']['id'],
            defaults={
                'display_name': entrant['user']['name'],
                'twitch_name': entrant['user'].get('twitch_name', None),
            }
        )
        if not new:
            user.twitch_name = entrant['user'].get('twitch_name', None)
            await user.save()
        race_history = await models.AsyncTournamentRace.filter(
            tournament=async_tournament_live_race.tournament,
            user=user,
            permalink__pool=async_tournament_live_race.pool,
            reattempted=False
        )

        # skip if they've already raced in this pool
        if race_history:
            continue

        # check if they have an active race already
        active_races = await models.AsyncTournamentRace.filter(
            tournament=async_tournament_live_race.tournament,
            user=user,
            status__in=['pending', 'in_progress'],
        )

        if active_races:
            continue

        await models.AsyncTournamentRace.create(
            tournament=async_tournament_live_race.tournament,
            permalink=permalink,
            user=user,
            thread_id=None,
            status='pending',
            live_race=async_tournament_live_race,
        )

        eligible_entrants_for_pool.append(user.display_name)

    return eligible_entrants_for_pool

# We need to update the entrants to in_progress and delete any pending entrants that didn't actually join
# TODO: We need to handle people who are accepted after the race room is locked.  We may need to refactor this to
# iterate through entrants a second time, and do a update_or_create, updating the status to in_progress if they
# already exist, and creating them if they don't.


async def process_async_tournament_start(async_tournament_live_race: models.AsyncTournamentLiveRace, race_room_data: dict):
    start_time = isodate.parse_datetime(race_room_data['started_at']).astimezone(pytz.utc)
    entrants = race_room_data.get('entrants', [])

    # update actual entrants to in_progress
    await models.AsyncTournamentRace.filter(
        live_race=async_tournament_live_race,
        status='pending',
        user__rtgg_id__in=[entrant['user']['id'] for entrant in entrants]
    ).update(
        status='in_progress',
        start_time=start_time
    )

    # delete any pending entrants that didn't actually join
    await models.AsyncTournamentRace.filter(
        live_race=async_tournament_live_race,
        status='pending'
    ).delete()

    async_tournament_live_race.status = 'in_progress'
    await async_tournament_live_race.save()

    in_progress_entrants = await models.AsyncTournamentRace.filter(
        live_race=async_tournament_live_race,
        status='in_progress'
    ).prefetch_related('user')

    return [entrant.user.display_name for entrant in in_progress_entrants]
