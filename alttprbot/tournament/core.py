import datetime
import logging
import json
import os
import isodate

import aiohttp
import discord
import gspread_asyncio
import pytz

from alttprbot.alttprgen import preset
from alttprbot import models
from alttprbot.util import gsheet, speedgaming
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.bot import discordbot
from alttprbot_discord.util import alttpr_discord
from alttprbot_racetime import bot as racetime

APP_URL = os.environ.get('APP_URL', 'https://sahasrahbotapi.synack.live')
TOURNAMENT_RESULTS_SHEET = os.environ.get('TOURNAMENT_RESULTS_SHEET', None)

class UnableToLookupUserException(SahasrahBotException):
    pass


class UnableToLookupEpisodeException(SahasrahBotException):
    pass


class TournamentPlayer(object):
    def __init__(self):
        pass

    @classmethod
    async def construct(cls, discord_id: int, guild):
        playerobj = cls()

        playerobj.data = await models.SRLNick.get_or_none(discord_user_id=discord_id)
        if playerobj.data is None:
            raise UnableToLookupUserException(f"Unable to pull nick data for {discord_id}")
        playerobj.discord_user = guild.get_member(int(discord_id))
        playerobj.name = playerobj.discord_user.name

        return playerobj

    @classmethod
    async def construct_discord_name(cls, discord_name: str, guild):
        playerobj = cls()

        playerobj.discord_user = guild.get_member_named(discord_name)
        if playerobj.discord_user is None:
            raise UnableToLookupUserException(f"Unable to lookup player {discord_name}")
        playerobj.name = discord_name
        playerobj.data = await models.SRLNick.get_or_none(discord_user_id=playerobj.discord_user.id)
        if playerobj.data is None:
            raise UnableToLookupUserException(f"Unable to pull nick data for {discord_name}")

        return playerobj


class TournamentRace(object):
    def __init__(self, episodeid: int, rtgg_handler):
        self.episodeid = int(episodeid)
        self.rtgg_handler = rtgg_handler

        self.players = []

        self.episode = None
        self.data = None

        self.rtgg_bot = None
        self.restream_team = None

    @classmethod
    async def construct(cls, episodeid, rtgg_handler):
        tournament_race = cls(episodeid, rtgg_handler)
        await discordbot.wait_until_ready()
        await tournament_race.update_data()
        return tournament_race

    @classmethod
    async def construct_race_room(cls, episodeid, category='alttpr', goal='Beat the game'):
        rtgg_bot = racetime.racetime_bots[category]

        tournament_race = cls(episodeid=episodeid, rtgg_handler=None)
        await discordbot.wait_until_ready()
        await tournament_race.update_data()

        handler = await rtgg_bot.startrace(
            goal=goal,
            invitational=True,
            unlisted=False,
            info=tournament_race.race_info,
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
            team_race=True if tournament_race.data.coop else False,
        )

        handler.tournament = tournament_race
        tournament_race.rtgg_handler = handler

        logging.info(handler.data.get('name'))
        await models.TournamentResults.update_or_create(srl_id=handler.data.get('name'), defaults={'episode_id': tournament_race.episodeid, 'event': tournament_race.event_slug, 'spoiler': None})

        for rtggid in tournament_race.player_racetime_ids:
            await handler.invite_user(rtggid)

        await tournament_race.send_player_room_info()

        if category != 'smw-hacks':
            await handler.send_message('Welcome. Use !tournamentrace (without any arguments) to roll your seed!  This should be done about 5 minutes prior to the start of your race.')

        return handler.data

    async def send_player_room_info(self):
        embed = discord.Embed(
            title=f"RT.gg Room Opened - {self.versus}",
            description=f"Greetings!  A RaceTime.gg race room has been automatically opened for you.\nYou may access it at {self.rtgg_bot.http_uri(self.rtgg_handler.data['url'])}\n\nEnjoy!",
            color=discord.Colour.blue(),
            timestamp=datetime.datetime.now()
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

    async def update_data(self):
        self.episode = await speedgaming.get_episode(self.episodeid)

        self.data = await models.Tournaments.get_or_none(schedule_type='sg', slug=self.event_slug)
        self.tournament_game = await models.TournamentGames.get_or_none(episode_id=self.episodeid)

        self.rtgg_bot = racetime.racetime_bots[self.data.category]
        self.restream_team = await self.rtgg_bot.get_team('sg-volunteers')

        if self.data is None:
            raise UnableToLookupEpisodeException('SG Episode ID not a recognized event.  This should not have happened.')

        if self.data.audit_channel_id is not None:
            self.audit_channel = discordbot.get_channel(self.data.audit_channel_id)

        if self.data.commentary_channel_id is not None:
            self.commentary_channel = discordbot.get_channel(self.data.commentary_channel_id)

        self.guild = discordbot.get_guild(self.data.guild_id)

        self.players = []
        for player in self.episode['match1']['players']:
            # first try a more concrete match of using the discord id cached by SG
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

    async def roll(self):
        pass

    async def can_gatekeep(self, rtgg_id):
        team_member_ids = [m['id'] for m in self.restream_team['members']]
        if rtgg_id in team_member_ids:
            return True

        nickname = await models.SRLNick.get_or_none(rtgg_id=rtgg_id)

        if not nickname:
            return False

        discord_user = self.guild.get_member(nickname.discord_user_id)

        if not discord_user:
            return False

        if helper_roles := self.data.helper_roles:
            if discord.utils.find(lambda m: m.name in helper_roles.split(','), discord_user.roles):
                return True

        return False

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
        return [p.data.rtgg_id for p in self.players]

    @property
    def player_names(self):
        return [p.name for p in self.players]

    @property
    def broadcast_channels(self):
        return [a['slug'] for a in self.episode['channels'] if not " " in a['name']]

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
        return info

    @property
    def race_info_rolled(self):
        info = f"{self.event_name} - {self.versus} - {self.friendly_name} - {self.seed_code}"
        if self.game_number:
            info += f" - Game #{self.game_number}"
        if self.broadcast_channels:
            info += f" - Restream(s) at {', '.join(self.broadcast_channels)}"
        return info

    @property
    def race_room_name(self):
        return self.rtgg_handler.data.get('name')

    @property
    def bracket_settings(self):
        if self.tournament_game:
            return self.tournament_game.settings

        return None

    async def create_embeds(self):
        pass

    async def send_audit_message(self, embed: discord.Embed):
        if self.audit_channel:
            await self.audit_channel.send(embed=embed)

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



async def create_tournament_race_room(episodeid, category='alttpr', goal='Beat the game'):
    rtgg_bot = racetime.racetime_bots[category]
    race = await models.TournamentResults.get_or_none(episode_id=episodeid)
    if race:
        async with aiohttp.request(method='get', url=rtgg_bot.http_uri(f"/{race.srl_id}/data"), raise_for_status=True) as resp:
            race_data = json.loads(await resp.read())
        status = race_data.get('status', {}).get('value')
        if not status == 'cancelled':
            return
        await race.delete()

    await TournamentRace.construct_race_room(episodeid, category=category, goal=goal)

async def race_recording_task():
    if TOURNAMENT_RESULTS_SHEET is None:
        return

    races = await models.TournamentResults.filter(written_to_gsheet=None)
    if races is None:
        return

    agcm = gspread_asyncio.AsyncioGspreadClientManager(gsheet.get_creds)
    agc = await agcm.authorize()
    wb = await agc.open_by_key(TOURNAMENT_RESULTS_SHEET)

    for race in races:
        logging.info(f"Recording {race.episode_id}")
        try:

            sheet_name = race.event
            wks = await wb.worksheet(sheet_name)

            async with aiohttp.request(
                    method='get',
                    url=f"{RACETIME_URL}/{race.srl_id}/data",
                    raise_for_status=True) as resp:
                race_data = json.loads(await resp.read())

            if race_data['status']['value'] == 'finished':
                winner = [e for e in race_data['entrants'] if e['place'] == 1][0]
                runnerup = [e for e in race_data['entrants'] if e['place'] in [2, None]][0]

                started_at = isodate.parse_datetime(race_data['started_at']).astimezone(pytz.timezone('US/Eastern'))
                await wks.append_row(values=[
                    race.episode_id,
                    started_at.strftime("%Y-%m-%d %H:%M:%S"),
                    f"{RACETIME_URL}/{race.srl_id}",
                    winner['user']['name'],
                    runnerup['user']['name'],
                    str(isodate.parse_duration(winner['finish_time'])) if isinstance(winner['finish_time'], str) else None,
                    str(isodate.parse_duration(runnerup['finish_time'])) if isinstance(runnerup['finish_time'], str) else None,
                    race.permalink,
                    race.spoiler
                ])
                race.status="RECORDED"
                race.written_to_gsheet=1
                await race.save()
            elif race_data['status']['value'] == 'cancelled':
                await race.delete()
            else:
                continue
        except Exception as e:
            logging.exception("Encountered a problem when attempting to record a race.")

    logging.debug('done')