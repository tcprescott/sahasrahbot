import logging
import os
from dataclasses import dataclass

import discord

from alttprbot import models
from alttprbot.util import speedgaming
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.bot import discordbot
from alttprbot_racetime import bot as racetime
from alttprbot_racetime.core import SahasrahBotRaceTimeBot
import dateutil.parser
import pytz

APP_URL = os.environ.get('APP_URL', 'https://sahasrahbotapi.synack.live')


class UnableToLookupUserException(SahasrahBotException):
    pass


@dataclass
class TournamentConfig:
    guild: discord.Guild

    racetime_category: str
    racetime_goal: str
    event_slug: str

    schedule_type: str = "sg"

    audit_channel: discord.TextChannel = None
    commentary_channel: discord.TextChannel = None
    mod_channel: discord.TextChannel = None
    scheduling_needs_channel: discord.TextChannel = None
    create_scheduled_events: bool = False

    scheduling_needs_tracker: bool = False

    admin_roles: list = None
    helper_roles: list = None
    commentator_roles: list = None
    mod_roles: list = None

    stream_delay: int = 0
    room_open_time: int = 35
    auto_record: bool = False
    gsheet_id: str = os.environ.get('TOURNAMENT_RESULTS_SHEET', None)
    hours_to_look_forward: int = 168

    lang: str = 'en'
    coop: bool = False


class TournamentPlayer(object):
    def __init__(self):
        self.data: models.Users = None
        self.discord_user: discord.Member = None

    @classmethod
    async def construct(cls, discord_id: int, guild: discord.Guild):
        playerobj = cls()

        if guild.chunked is False:
            await guild.chunk(cache=True)

        playerobj.data = await models.Users.get_or_none(discord_user_id=discord_id)
        if playerobj.data is None:
            raise UnableToLookupUserException(f"Unable to pull nick data for {discord_id}")
        playerobj.discord_user = guild.get_member(int(discord_id))

        return playerobj

    @classmethod
    async def construct_discord_name(cls, discord_name: str, guild: discord.Guild):
        playerobj = cls()

        if guild.chunked is False:
            await guild.chunk(cache=True)

        playerobj.discord_user = guild.get_member_named(discord_name)
        if playerobj.discord_user is None:
            raise UnableToLookupUserException(f"Unable to lookup player {discord_name}")
        playerobj.data = await models.Users.get_or_none(discord_user_id=playerobj.discord_user.id)
        if playerobj.data is None:
            raise UnableToLookupUserException(f"Unable to pull nick data for {discord_name}")

        return playerobj

    @property
    def rtgg_id(self):
        return self.data.rtgg_id

    @property
    def name(self):
        return self.discord_user.name


class TournamentRace(object):
    def __init__(self, episodeid: int = None, rtgg_handler=None):
        try:
            self.episodeid = int(episodeid)
        except TypeError:
            self.episodeid = episodeid

        self.rtgg_handler = rtgg_handler

        self.players = []

        self.episode = None
        self.data: TournamentConfig = None

        self.rtgg_bot = None
        self.restream_team = None

    @classmethod
    async def construct(cls, episodeid, rtgg_handler):
        tournament_race = cls(episodeid, rtgg_handler)

        logging.info(f"TournamentRace: Waiting for discordbot to be ready to construct {episodeid}")
        await discordbot.wait_until_ready()
        logging.info(f"TournamentRace: Finished constructing {episodeid}")
        tournament_race.data = await tournament_race.configuration()
        await tournament_race.update_data()

        return tournament_race

    @classmethod
    async def construct_with_episode_data(cls, episode: dict, rtgg_handler):
        tournament_race = cls(episode['id'], rtgg_handler)
        tournament_race.episode = episode

        await discordbot.wait_until_ready()
        tournament_race.data = await tournament_race.configuration()
        await tournament_race.update_data(update_episode=False)

        return tournament_race

    @classmethod
    async def construct_race_room(cls, episodeid):
        tournament_race = cls(episodeid=episodeid, rtgg_handler=None)

        await discordbot.wait_until_ready()
        tournament_race.data = await tournament_race.configuration()
        await tournament_race.update_data()

        handler = await tournament_race.create_race_room()

        handler.tournament = tournament_race
        tournament_race.rtgg_handler = handler

        logging.info(handler.data.get('name'))
        await models.TournamentResults.update_or_create(srl_id=handler.data.get('name'), defaults={'episode_id': tournament_race.episodeid, 'event': tournament_race.event_slug, 'spoiler': None})

        for rtggid in tournament_race.player_racetime_ids:
            await handler.invite_user(rtggid)

        await tournament_race.send_player_room_info()

        await tournament_race.send_room_welcome()

        await tournament_race.on_room_creation()

        return handler.data

    @classmethod
    async def get_config(cls):
        tournament_race = cls()

        await discordbot.wait_until_ready()
        tournament_race.data = await tournament_race.configuration()
        return tournament_race

    async def configuration(self) -> TournamentConfig:
        self.data = None

    async def send_player_room_info(self):
        embed = discord.Embed(
            title=f"RT.gg Room Opened - {self.versus}",
            description=f"Greetings!  A RaceTime.gg race room has been automatically opened for you.\nYou may access it at {self.rtgg_bot.http_uri(self.rtgg_handler.data['url'])}\n\nEnjoy!",
            color=discord.Colour.blue(),
            timestamp=discord.utils.utcnow()
        )

        for name, player in self.player_discords:
            if player is None:
                logging.info(f'Could not DM {name}')
                continue
            try:
                await player.send(embed=embed)
            except discord.HTTPException:
                logging.info(f'Could not send room opening DM to {name}')
                continue

    async def send_room_welcome(self):
        pass

    async def on_room_creation(self):
        pass

    async def on_room_resume(self):
        pass

    async def on_race_start(self):
        pass

    async def on_race_pending(self):
        pass

    async def process_tournament_race(self, args, message):
        pass

    async def create_race_room(self):
        self.rtgg_handler = await self.rtgg_bot.startrace(
            goal=self.data.racetime_goal,
            invitational=True,
            unlisted=False,
            info_user=self.race_info,
            start_delay=15,
            time_limit=24,
            streaming_required=True,
            auto_start=True,
            allow_comments=True,
            hide_comments=True,
            allow_prerace_chat=True,
            allow_midrace_chat=True,
            allow_non_entrant_chat=False,
            chat_message_delay=0,
            team_race=self.data.coop,
        )
        return self.rtgg_handler

    async def update_data(self, update_episode=True):
        if update_episode:
            self.episode = await speedgaming.get_episode(self.episodeid)

        self.tournament_game = await models.TournamentGames.get_or_none(episode_id=self.episodeid)

        self.rtgg_bot: SahasrahBotRaceTimeBot = racetime.racetime_bots[self.data.racetime_category]
        self.restream_team = await self.rtgg_bot.get_team('sg-volunteers')

        self.players = []
        for player in self.episode['match1']['players']:
            # first try a more concrete match of using the discord id cached by SG
            if player['publicStream'] == 'ignore':
                continue
            looked_up_player = await self.make_tournament_player(player)
            self.players.append(looked_up_player)

    async def make_tournament_player(self, player):
        if not player['discordId'] == "":
            looked_up_player = await TournamentPlayer.construct(discord_id=player['discordId'], guild=self.guild)
        else:
            looked_up_player = None

        # then, if that doesn't work, try their discord tag kept by SG
        if looked_up_player is None and not player['discordTag'] == '':
            looked_up_player = await TournamentPlayer.construct_discord_name(discord_name=player['discordTag'], guild=self.guild)

        # and failing all that, bomb
        if looked_up_player is None:
            raise UnableToLookupUserException(
                f"Unable to lookup the player `{player['displayName']}`.  Please contact a Tournament moderator for assistance.")

        return looked_up_player

    async def can_gatekeep(self, rtgg_id):
        team_member_ids = [m['id'] for m in self.restream_team['members']]
        if rtgg_id in team_member_ids:
            return True

        nickname = await models.Users.get_or_none(rtgg_id=rtgg_id)

        if not nickname:
            return False

        if self.guild.chunked is False:
            await self.guild.chunk(cache=True)

        discord_user = self.guild.get_member(nickname.discord_user_id)

        if not discord_user:
            return False

        return any([True for x in self.data.helper_roles if x in discord_user.roles])

    @property
    def guild(self):
        return self.data.guild

    @property
    def submission_form(self):
        return None

    @property
    def lang(self):
        return self.data.lang

    @property
    def submit_link(self):
        return f"{APP_URL}/submit/{self.event_slug}?episode_id={self.episodeid}"

    @property
    def game_number(self):
        if self.tournament_game:
            return self.tournament_game.game_number
        return ""

    @property
    def event_name(self):
        return self.episode['event']['shortName']

    @property
    def event_slug(self):
        return self.episode['event']['slug']

    @property
    def friendly_name(self):
        return self.episode['match1']['title']

    @property
    def versus(self):
        separator = ' vs. '
        if len(self.player_names) > 2:
            separator = ', '
        return separator.join(self.player_names)

    @property
    def player_discords(self):
        return [(p.name, p.discord_user) for p in self.players]

    @property
    def player_racetime_ids(self):
        return [p.rtgg_id for p in self.players]

    @property
    def player_names(self):
        return [p.name for p in self.players]

    @property
    def player_twitch_names(self):
        return [p['streamingFrom'] for p in self.episode['match1']['players']]

    @property
    def broadcast_channels(self):
        return [a['name'] for a in self.episode['channels'] if not " " in a['name']]

    @property
    def broadcast_channel_links(self):
        return ', '.join([f"[{a}](https://twitch.tv/{a})" for a in self.broadcast_channels])

    @property
    def seed_code(self):
        return None

    @property
    def race_info(self):
        info = f"{self.event_name} - {self.versus} - {self.friendly_name}"
        if self.game_number:
            info += f" - Game #{self.game_number}"
        if self.broadcast_channels:
            info += f" - Restream(s) at {', '.join(self.broadcast_channels)}"
        info += f" - {self.episodeid}"
        return info

    @property
    def race_room_name(self):
        return self.rtgg_handler.data.get('name')

    @property
    def audit_channel(self):
        return self.data.audit_channel

    @property
    def commentary_channel(self):
        return self.data.commentary_channel

    @property
    def race_start_time(self):
        return dateutil.parser.parse(self.episode['whenCountdown'])

    @property
    def race_start_time_restream(self):
        return dateutil.parser.parse(self.episode['when'])

    def string_time(self, date):
        return date.astimezone(self.timezone).strftime("%-I:%M %p")

    @property
    def timezone(self):
        return pytz.timezone('US/Eastern')

    @property
    def hours_before_room_open(self):
        return ((self.data.stream_delay + self.data.room_open_time)/60)

    async def create_embeds(self):
        pass

    async def process_submission_form(self, payload, submitted_by):
        pass

    async def send_audit_message(self, message=None, embed: discord.Embed = None):
        if self.audit_channel:
            await self.audit_channel.send(content=message, embed=embed)

    async def send_commentary_message(self, embed: discord.Embed):
        if self.commentary_channel and len(self.broadcast_channels) > 0:
            await self.commentary_channel.send(embed=embed)

    async def send_player_message(self, name: str, player: discord.Member, embed: discord.Embed):
        if self.rtgg_handler is None:
            raise SahasrahBotException("No RaceTime.gg handler associated with this tournament game.")

        if player is None:
            await self.audit_channel.send(f"@here could not send DM to {name}", allowed_mentions=discord.AllowedMentions(everyone=True))
            await self.rtgg_handler.send_message(f"Could not send DM to {name}.  Please contact a Tournament Moderator for assistance.")
        try:
            await player.send(embed=embed)
        except discord.HTTPException:
            if self.audit_channel:
                await self.audit_channel.send(f"@here could not send DM to {player.name}#{player.discriminator}", allowed_mentions=discord.AllowedMentions(everyone=True))
            await self.rtgg_handler.send_message(f"Could not send DM to {player.name}#{player.discriminator}.  Please contact a Tournament Moderator for assistance.")

    async def send_race_submission_form(self, warning=False):
        if self.submission_form is None:
            return

        if self.tournament_game and self.tournament_game.submitted and not warning:
            return

        if warning:
            msg = (
                f"Your upcoming race room cannot be created because settings have not submitted: `{self.versus}`!\n\n"
                f"For your convenience, please visit {self.submit_link} to submit the settings.\n\n"
            )
        else:
            msg = (
                f"Greetings!  Do not forget to submit settings for your upcoming race: `{self.versus}`!\n\n"
                f"For your convenience, please visit {self.submit_link} to submit the settings.\n\n"
            )

        for name, player in self.player_discords:
            if player is None:
                continue
            logging.info("Sending tournament submit reminder to %s.", name)
            await player.send(msg)

        await models.TournamentGames.update_or_create(episode_id=self.episodeid, defaults={'event': self.event_slug, 'submitted': 1})