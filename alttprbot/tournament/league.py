import datetime
import json
import os
import random

import aiohttp
import discord
import gspread_asyncio
from alttprbot.alttprgen import mystery, preset, spoilers
from alttprbot.database import (config, spoiler_races, tournament_results,
                                twitch_command_text)
from alttprbot.exceptions import SahasrahBotException
# from alttprbot.util import srl
from alttprbot_discord.bot import discordbot
from alttprbot_discord.util import alttpr_discord
from config import Config as c  # pylint: disable=no-name-in-module
from oauth2client.service_account import ServiceAccountCredentials
from pytz import timezone

from ..util import speedgaming

tz = timezone('US/Eastern')

WEEKDATA = {
    '1': {
        'type': 'preset',
        'preset': 'dungeons',
        'coop': True,
        'friendly_name': 'Week 1 - All Dungeons Co-op Info Share'
    },
    '2': {
        'type': 'preset',
        'preset': 'open',
        'friendly_name': 'Week 2 - Open'
    },
    '3': {
        'type': 'preset',
        'preset': 'casualboots',
        'friendly_name': 'Week 3 - Enemizer'
    },
    '4': {
        'type': 'spoiler',
        'preset': 'keysanity',
        'studyperiod': 0,
        'friendly_name': 'Week 4 - Piloted Spoiler Keysanity'
    },
    '5': {
        'type': 'mystery',
        'weightset': 'league',
        'friendly_name': 'Week 5 - Mystery'
    },
    '6': {
        'type': 'preset',
        'preset': 'adkeys',
        'friendly_name': 'Week 6 - All Dungeons Keysanity'
    },
    '7': {
        'type': 'preset',
        'preset': 'enemizer',
        'coop': True,
        'friendly_name': 'Week 7 - Enemizer Co-op Info Share'
    }
}

PLAYOFFDATA = {
    1: {
        'type': 'preset',
        'preset': 'open',
        'friendly_name': 'Playoffs Game 1 - Open'
    },
    2: {
        'type': 'preset',
        'preset': 'casualboots',
        'friendly_name': 'Playoffs Game 2 - Standard w/ Sword and Boots'
    },
    3: {
        'type': 'gsheet',
        'friendly_name': 'Playoffs Game 3'
    },
    4: {
        'type': 'gsheet',
        'friendly_name': 'Playoffs Game 4'
    },
    5: {
        'type': 'gsheet',
        'friendly_name': 'Playoffs Game 5'
    }
}

SETTINGSMAP = {
    'Standard': 'standard',
    'Maps/Compasses': 'mc',
    'Maps/Compasses/Small Keys': 'mcs',
    'Keysanity': 'full',
    'Defeat Ganon': 'ganon',
    'Fast Ganon': 'fast_ganon',
    'All Dungeons': 'dungeons',
    'Open': 'open',
    'Inverted': 'inverted',
    'Randomized': 'randomized',
    'Assured': 'assured',
    'Vanilla': 'vanilla',
    'Swordless': 'swordless',
    'Hard': 'hard',
    'Normal': 'normal',
    'Off': 'off',
    'Enemy Shuffle': 'enemies',
    'Boss Shuffle': 'bosses',
    'Enemies and Bosses': 'full_enemizer'
}


class WeekNotFoundException(SahasrahBotException):
    pass


class SettingsSubmissionNotFoundException(SahasrahBotException):
    pass


async def settings_sheet(episodeid):
    sheet = SettingsSheet(episodeid)
    await sheet._init()
    return sheet


class SettingsSheet():
    def __init__(self, episodeid):
        self.agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
        self.episodeid = episodeid

    async def _init(self):
        self.agc = await self.agcm.authorize()
        self.wb = await self.agc.open_by_key('1K3_Eccv8fG-ZPXhbX4J6bNV-9sQf9_IiJzl6ycvPtGE')
        self.wks = await self.wb.get_worksheet(0)

        self.headers = await self.wks.row_values(1)

        for idx, row in enumerate(await self.wks.get_all_records()):
            if row['SpeedGaming Episode ID'] == int(self.episodeid):
                self.rowid = idx+2
                self.row = row
                return row
        raise SettingsSubmissionNotFoundException(
            'Settings submission not found at <https://docs.google.com/spreadsheets/d/1K3_Eccv8fG-ZPXhbX4J6bNV-9sQf9_IiJzl6ycvPtGE/edit#gid=1883794426>.  Please submit settings.')

    async def write_gen_date(self):
        date_gen_column = self.headers.index('Date Generated')+1
        await self.wks.update_cell(row=self.rowid, col=date_gen_column, value=datetime.datetime.now(tz).isoformat())

    def is_generated(self):
        if not self.row['Date Generated'] == '':
            return True
        else:
            return False

    @property
    def settings(self):
        goal = random.choice(['dungeons', 'ganon', 'fast_ganon']) if self.row['Goal'] == 'Random' else SETTINGSMAP[self.row['Goal']]
        world_state = random.choice(['open', 'standard', 'inverted']) if self.row['World State'] == 'Random' else SETTINGSMAP[self.row['World State']]
        swords = random.choice(['assured','randomized', 'vanilla', 'swordless']) if self.row['Swords'] == 'Random' else SETTINGSMAP[self.row['Swords']]
        enemizer = random.choices(['off', 'enemies', 'bosses', 'full_enemizer'], [50, 16, 16, 16]) if self.row['Enemizer'] == 'Random' else SETTINGSMAP[self.row['Enemizer']]
        dungeon_items = random.choice(['standard', 'mc', 'mcs', 'full']) if self.row['Dungeon Item Shuffle'] == 'Random' else SETTINGSMAP[self.row['Dungeon Item Shuffle']]
        item_pool = random.choice(['normal', 'hard']) if self.row['Item Pool'] == 'Random' else SETTINGSMAP[self.row['Item Pool']]

        boss_shuffle = 'none'
        enemy_shuffle = 'none'

        if enemizer in ['enemies', 'full_enemizer']:
            enemy_shuffle = 'shuffled'

        if enemizer in ['bosses', 'full_enemizer']:
            boss_shuffle = 'full'

        return {
            "allow_quickswap": True,
            "glitches": "none",
            "item_placement": "advanced",
            "dungeon_items": dungeon_items,
            "accessibility": "items",
            "goal": goal,
            "crystals": {
                "ganon": '7',
                "tower": '7',
            },
            "mode": world_state,
            "entrances": "none",
            "hints": "off",
            "weapons": swords,
            "item": {
                "pool": item_pool,
                "functionality": "normal"
            },
            "tournament": True,
            "spoilers": "off",
            "lang": "en",
            "enemizer": {
                    "boss_shuffle": boss_shuffle,
                    "enemy_shuffle": enemy_shuffle,
                    "enemy_damage": "default",
                    "enemy_health": "default"
            }
        }


async def league_race(episodeid: int, week=None):
    race = LeagueRace(episodeid, week)
    await race._init()
    return race

class LeaguePlayer():
    def __init__(self):
        pass

    @classmethod
    async def construct(cls, name, guild, name_type='twitch'):
        playerobj = cls()

        async with aiohttp.request(
            method='get',
            url='https://alttprleague.com/json_ep/player/',
            params={
                name_type: name,
            }
        ) as resp:
            r = await resp.json()
            players = r['results']

        if players is not None:
            if name_type == 'twitch':
                player = [p for p in players if p['twitch_name'].lower() == name.lower()][0]
            elif name_type == 'discord':
                player = [p for p in players if p['discord'] == name][0]
            elif name_type == 'rtgg':
                player = [p for p in players if p['rtgg_name'] == name][0]
            else:
                raise Exception('Invalid name type.')

            playerobj.data = player

            playerobj.discord_user = guild.get_member_named(player['discord'])

        return playerobj

class LeagueRace():
    def __init__(self, episodeid: int, week=None):
        self.episodeid = int(episodeid)
        self.week = week
        self.players = []

    async def _init(self):
        guild_id = await config.get(0, 'AlttprLeagueServer')
        self.guild = discordbot.get_guild(int(guild_id))

        if self.week is None:
            self.week = await config.get(guild_id, 'AlttprLeagueWeek')

        if self.week not in WEEKDATA and not self.week == 'playoffs':
            raise WeekNotFoundException(f'Week {self.week} was not found!')

        self.episode = await speedgaming.get_episode(self.episodeid)

        twitch_names = [p['streamingFrom'] if p['publicStream'] == '' else p['publicStream'] for p in self.episode['match1']['players']]
        for twitch_name in twitch_names:
            self.players.append(
                await LeaguePlayer.construct(name=twitch_name, guild=self.guild, name_type='twitch')
            )

        if self.week == 'playoffs':
            self.sheet_settings = await settings_sheet(self.episodeid)
            self.type = PLAYOFFDATA[self.sheet_settings.row['Game Number']]['type']
            self.friendly_name = PLAYOFFDATA[self.sheet_settings.row['Game Number']
                                             ]['friendly_name']
            self.spoiler_log_url = None

            if self.type == 'preset':
                self.preset = PLAYOFFDATA[self.sheet_settings.row['Game Number']]['preset']
                self.seed, self.preset_dict = await preset.get_preset(self.preset, nohints=True, allow_quickswap=True)
            elif self.type == 'gsheet':
                self.preset = None
                self.preset_dict = None
                self.seed = await alttpr_discord.alttpr(
                    settings=self.sheet_settings.settings
                )
            await self.sheet_settings.write_gen_date()
        else:
            self.type = WEEKDATA[self.week]['type']
            self.friendly_name = WEEKDATA[self.week]['friendly_name']
            self.spoiler_log_url = None

            if self.type == 'preset':
                self.preset = WEEKDATA[self.week]['preset']
                self.seed, self.preset_dict = await preset.get_preset(self.preset, nohints=True, allow_quickswap=True)
            elif self.type == 'mystery':
                self.weightset = WEEKDATA[self.week]['weightset']
                self.seed = await mystery.generate_random_game(weightset=self.weightset, spoilers="mystery", tournament=True)
            elif self.type == 'spoiler':
                self.preset = WEEKDATA[self.week]['preset']
                self.studyperiod = WEEKDATA[self.week]['studyperiod']
                self.seed, self.preset_dict, self.spoiler_log_url = await spoilers.generate_spoiler_game(WEEKDATA[self.week]['preset'])
                
            else:
                raise SahasrahBotException(
                    'Week type not found, something went horribly wrong...')

    @property
    def player_discords(self):
        return [(p.data['name'], p.discord_user) for p in self.players]

    @property
    def player_names(self):
        return [p.data['name'] for p in self.players]

    @property
    def team_names(self):
        return list(set([p.data['team_name'] for p in self.players]))

    @property
    def division_names(self):
        return list(set([p.data['division_name'] for p in self.players]))

    @property
    def division_urls(self):
        return list(set([p.data['division_url'] for p in self.players]))

    @property
    def players_by_team(self):
        result = {}
        for team in self.team_names:
            result[team] = [p for p in self.players if p.data['team_name'] == team]
        return result

    @property
    def twitch_mode_command(self):
        if self.week == 'playoffs':
            return f"The settings for this race is \"{self.seed.generated_goal}\"!  It is game number {self.sheet_settings.row['Game Number']} of this series."

        if self.type == 'preset':
            return f"The preset for this race is {self.preset}."

        if self.type == 'spoiler':
            return f"This is a {self.preset} spoiler race."

        if self.type == 'mystery':
            return f"The weightset for this race is {self.weightset}."


async def process_league_race(handler, episodeid, week=None):
    await handler.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")

    generated_league_race = await league_race(episodeid=episodeid, week=week)
    teams = generated_league_race.players_by_team

    t = []
    for team in teams:
        t.append(' and '.join([p.data['name'] for p in teams[team]]))

    goal = f"ALTTPR League - {' vs. '.join(t)} - {generated_league_race.friendly_name}"


    await handler.set_raceinfo(goal, overwrite=True)

    embed = await generated_league_race.seed.embed(
        name=goal,
        notes=' vs. '.join(generated_league_race.team_names),
        emojis=discordbot.emojis
    )

    tournament_embed = await generated_league_race.seed.tournament_embed(
        name=goal,
        notes=' vs. '.join(generated_league_race.team_names),
        emojis=discordbot.emojis
    )

    broadcast_channels = [
        a['name'] for a in generated_league_race.episode['channels'] if not " " in a['name']]

    if len(broadcast_channels) > 0:
        twitch_mode_text = generated_league_race.twitch_mode_command
        twitch_teams_text = f"This race is between {' vs. '.join(generated_league_race.team_names)}.  Check out rankings for division(s) {', '.join(generated_league_race.division_names)} at {' '.join(generated_league_race.division_urls)}"

        for channel in broadcast_channels:
            await twitch_command_text.insert_command_text(channel.lower(), "mode", twitch_mode_text)
            await twitch_command_text.insert_command_text(channel.lower(), "teams", twitch_teams_text)

        tournament_embed.insert_field_at(
            0, name="Broadcast Channels", value=', '.join([f"[{a}](https://twitch.tv/{a})" for a in broadcast_channels]), inline=False)
        embed.insert_field_at(
            0, name="Broadcast Channels", value=', '.join([f"[{a}](https://twitch.tv/{a})" for a in broadcast_channels]), inline=False)

    audit_channel_id = await config.get(generated_league_race.guild.id, 'AlttprLeagueAuditChannel')
    if audit_channel_id is not None:
        audit_channel = discordbot.get_channel(int(audit_channel_id))
        await audit_channel.send(embed=embed)

    commentary_channel_id = await config.get(generated_league_race.guild.id, 'AlttprLeagueCommentaryChannel')
    if commentary_channel_id is not None and len(broadcast_channels) > 0:
        commentary_channel = discordbot.get_channel(int(commentary_channel_id))
        await commentary_channel.send(embed=tournament_embed)

    for name, player in generated_league_race.player_discords:
        if player is None:
            await audit_channel.send(f"@here could not send DM to {name}")
            continue
        try:
            await player.send(embed=embed)
        except discord.HTTPException:
            if audit_channel is not None:
                await audit_channel.send(f"@here could not send DM to {player.name}#{player.discriminator}")

    if generated_league_race.type == 'spoiler':
        await spoiler_races.insert_spoiler_race(handler.data.get('name'), generated_league_race.spoiler_log_url, generated_league_race.studyperiod)

    await tournament_results.insert_tournament_race(
        srl_id=handler.data.get('name'),
        episode_id=generated_league_race.episodeid,
        permalink=generated_league_race.seed.url,
        event='alttprleague_s3',
        week=generated_league_race.week,
        spoiler=generated_league_race.spoiler_log_url if generated_league_race.spoiler_log_url else None
    )

    await handler.send_message("Seed has been generated, you should have received a DM in Discord.  Please contact a League Moderator if you haven't received the DM.")


async def process_league_race_start(handler):
    race_id = handler.data.get('name')

    if race_id is None:
        return

    race = await tournament_results.get_active_tournament_race(race_id)

    if race is None:
        return

    if os.environ.get("LEAGUE_SUBMIT_GAME_SECRET"):
        await aiohttp.request(
            method='get',
            url='https://alttprleague.com/json_ep/submit-game',
            params={
                'slug': race_id,
                'sgl': race['episode_id'],
                'secret': os.environ.get("LEAGUE_SUBMIT_GAME_SECRET")
            }
        )
    else:
        print(f"Would have reported match {race_id} for episode {race['episode_id']}")

    await tournament_results.update_tournament_results(race_id, status="STARTED")

def get_creds():
    return ServiceAccountCredentials.from_json_keyfile_dict(c.gsheet_api_oauth,
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets'])
