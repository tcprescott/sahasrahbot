import datetime
import os
import random
import logging
import json

import aiohttp
import discord
import gspread_asyncio
from pytz import timezone

from alttprbot.alttprgen import mystery, preset, spoilers
from alttprbot.database import (config, spoiler_races, tournament_results,
                                twitch_command_text, srlnick)
from alttprbot.util import gsheet, speedgaming
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.bot import discordbot
from alttprbot_discord.util import alttpr_discord
from alttprbot_racetime.bot import racetime_bots
# from config import Config as c

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
        'friendly_name': 'Week 3 - Casual Boots'
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


class UnableToLookupUserException(SahasrahBotException):
    pass


async def settings_sheet(episodeid):
    sheet = SettingsSheet(episodeid)
    await sheet._init()
    return sheet


class SettingsSheet():
    def __init__(self, episodeid):
        self.agcm = gspread_asyncio.AsyncioGspreadClientManager(gsheet.get_creds)
        self.episodeid = episodeid

    async def _init(self):
        self.agc = await self.agcm.authorize()
        self.wb = await self.agc.open_by_key('1ZDlb_d2jdYqvRf9p_HPMjtKw9hOF3xeu9028eu8Df5A')
        self.wks = await self.wb.get_worksheet(0)

        self.headers = await self.wks.row_values(1)

        for idx, row in enumerate(await self.wks.get_all_records()):
            if row['SpeedGaming Episode ID'] == int(self.episodeid):
                self.rowid = idx+2
                self.row = row
                return row
        raise SettingsSubmissionNotFoundException(
            'Settings submission not found at <https://docs.google.com/spreadsheets/d/1ZDlb_d2jdYqvRf9p_HPMjtKw9hOF3xeu9028eu8Df5A/edit#gid=1883794426>.  Please submit settings.')

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
        goal = random.choice(['dungeons', 'ganon', 'fast_ganon']
                             ) if self.row['Goal'] == 'Random' else SETTINGSMAP[self.row['Goal']]
        world_state = random.choice(
            ['open', 'standard', 'inverted']) if self.row['World State'] == 'Random' else SETTINGSMAP[self.row['World State']]
        swords = random.choice(['assured', 'randomized', 'vanilla', 'swordless']
                               ) if self.row['Swords'] == 'Random' else SETTINGSMAP[self.row['Swords']]
        enemizer = random.choices(['off', 'enemies', 'bosses', 'full_enemizer'], [
                                  40, 20, 20, 20]) if self.row['Enemizer'] == 'Random' else SETTINGSMAP[self.row['Enemizer']]
        dungeon_items = random.choices(['standard', 'mc', 'mcs', 'full'], [
                                       40, 20, 20, 20]) if self.row['Dungeon Item Shuffle'] == 'Random' else SETTINGSMAP[self.row['Dungeon Item Shuffle']]
        item_pool = random.choice(
            ['normal', 'hard']) if self.row['Item Pool'] == 'Random' else SETTINGSMAP[self.row['Item Pool']]

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
                    "boss_shuffle": "full" if enemizer in ["bosses", "full_enemizer"] else "none",
                    "enemy_shuffle": "shuffled" if enemizer in ["enemies", "full_enemizer"] else "none",
                    "enemy_damage": "default",
                    "enemy_health": "default"
            }
        }


class LeaguePlayer():
    def __init__(self):
        pass

    @classmethod
    async def construct(cls, name, guild, name_type='twitch'):
        playerobj = cls()

        name_type_map = {
            'twitch': 'twitch',
            'discord': 'discord',
            'display_name': 'discord',
            'discord_id': 'discord_id',
            'rtgg': 'rtgg_name',
            'rtgg_id': 'rtgg_id',
        }

        name = name.strip()
        if name_type == "discord_id":
            name = int(name)

        async with aiohttp.request(
            method='get',
            url='https://alttprleague.com/json_ep/player/',
            params={
                name_type_map[name_type]: name,
            },
            raise_for_status=True
        ) as resp:
            r = await resp.json()
            players = r['results']

        if players is None:
            return None

        if name_type == 'twitch':
            player = [p for p in players if p['twitch_name'].lower()
                      == name.lower()][0]
        elif name_type == 'discord':
            player = [p for p in players if p['discord'] == name][0]
        elif name_type == 'display_name':
            player = players[0]
        elif name_type == 'discord_id':
            player = [p for p in players if p['discord_id'] == name][0]
        elif name_type == 'rtgg':
            player = [p for p in players if p['rtgg_name'] == name][0]
        else:
            raise Exception('Invalid name type.')

        playerobj.data = player

        if player.get('discord_id', None) is None:
            playerobj.discord_user = guild.get_member_named(player['discord'])
        else:
            playerobj.discord_user = guild.get_member(player['discord_id'])

        return playerobj


class LeagueRace():
    def __init__(self, episodeid: int, week=None, create_seed=True):
        self.episodeid = int(episodeid)
        self.week = week
        self.create_seed = create_seed
        self.players = []

    @classmethod
    async def construct(cls, episodeid, week=None, create_seed=True):
        league_race = cls(episodeid, week, create_seed)
        guild_id = await config.get(0, 'AlttprLeagueServer')
        league_race.guild = discordbot.get_guild(int(guild_id))

        if league_race.week is None:
            league_race.week = await config.get(guild_id, 'AlttprLeagueWeek')

        if league_race.week not in WEEKDATA and not league_race.week == 'playoffs':
            raise WeekNotFoundException(
                f'Week {league_race.week} was not found!')

        league_race.episode = await speedgaming.get_episode(league_race.episodeid)

        for player in league_race.episode['match1']['players']:
            # first try a more concrete match of using the discord id cached by SG
            looked_up_player = await league_race.make_league_player_from_sg(player)
            league_race.players.append(looked_up_player)

        if league_race.create_seed:
            if league_race.is_playoff:
                await league_race._roll_playoffs()
            else:
                await league_race._roll_general()

        return league_race

    async def make_league_player_from_sg(self, player):
        try:
            looked_up_player = await LeaguePlayer.construct(name=player['discordId'], guild=self.guild, name_type='discord_id')
        except ValueError:
            looked_up_player = None

        # then, if that doesn't work, try their discord tag kept by SG
        if looked_up_player is None and not player['discordTag'] == '':
            looked_up_player = await LeaguePlayer.construct(name=player['discordTag'], guild=self.guild, name_type='discord')

        # then, if that doesn't work, try their streamingFrom name
        if looked_up_player is None and not player['streamingFrom'] == '':
            looked_up_player = await LeaguePlayer.construct(name=player['streamingFrom'], guild=self.guild, name_type='twitch')

        # finally, try publicStream
        if looked_up_player is None and not player['publicStream'] == '':
            looked_up_player = await LeaguePlayer.construct(name=player['publicStream'], guild=self.guild, name_type='twitch')

        # a final hail mary pass
        if looked_up_player is None and not player['displayName'] == '':
            looked_up_player = await LeaguePlayer.construct(name=player['displayName'], guild=self.guild, name_type='display_name')

        # and failing all that, bomb
        if looked_up_player is None:
            raise UnableToLookupUserException(
                f"Unable to lookup the player `{player['displayName']}`.  Please contact a league moderator for assistance.")

        return looked_up_player

    async def _roll_playoffs(self):
        self.sheet_settings = await settings_sheet(self.episodeid)
        self.spoiler_log_url = None

        if self.gen_type == 'preset':
            self.preset = PLAYOFFDATA[self.sheet_settings.row['Game Number']]['preset']
            self.seed, self.preset_dict = await preset.get_preset(self.preset, nohints=True, allow_quickswap=True)
        elif self.gen_type == 'gsheet':
            self.preset = None
            self.preset_dict = None
            self.seed = await alttpr_discord.alttpr(
                settings=self.sheet_settings.settings
            )
        await self.sheet_settings.write_gen_date()

    async def _roll_general(self):
        self.spoiler_log_url = None

        if self.gen_type == 'preset':
            self.preset = WEEKDATA[self.week]['preset']
            self.seed, self.preset_dict = await preset.get_preset(self.preset, nohints=True, allow_quickswap=True)
        elif self.gen_type == 'mystery':
            self.weightset = WEEKDATA[self.week]['weightset']
            self.seed = await mystery.generate_random_game(weightset=self.weightset, spoilers="mystery", tournament=True)
        elif self.gen_type == 'spoiler':
            self.preset = WEEKDATA[self.week]['preset']
            self.studyperiod = WEEKDATA[self.week]['studyperiod']
            self.seed, self.preset_dict, self.spoiler_log_url = await spoilers.generate_spoiler_game(WEEKDATA[self.week]['preset'])
        else:
            raise SahasrahBotException(
                'Week type not found, something went horribly wrong...')

    @property
    def is_playoff(self):
        return self.week == 'playoffs'

    @property
    def friendly_name(self):
        if self.is_playoff:
            return PLAYOFFDATA[self.sheet_settings.row['Game Number']]['friendly_name']

        return WEEKDATA[self.week]['friendly_name']

    @property
    def gen_type(self):
        if self.is_playoff:
            return PLAYOFFDATA[self.sheet_settings.row['Game Number']]['type']

        return WEEKDATA[self.week]['type']

    @property
    def coop(self):
        if self.week == 'playoffs':
            return False

        return WEEKDATA[self.week].get('coop', False)

    @property
    def versus(self):
        t = []
        for team in self.players_by_team:
            t.append(' and '.join([p.data['name']
                                   for p in self.players_by_team[team]]))

        return ' vs. '.join(t)

    @property
    def versus_and_team(self):
        t = []
        for team in self.players_by_team:
            t.append(
                f"{' and '.join([p.data['name']for p in self.players_by_team[team]])} ({team})")

        return ' vs. '.join(t)

    @property
    def team_versus(self):
        return ' vs. '.join(self.team_names)

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
            result[team] = [
                p for p in self.players if p.data['team_name'] == team]
        return result

    @property
    def twitch_mode_command(self):
        if self.week == 'playoffs':
            return f"The settings for this race is \"{self.seed.generated_goal}\"!  It is game number {self.sheet_settings.row['Game Number']} of this series."

        if self.gen_type == 'preset':
            return f"The preset for this race is {self.preset}."

        if self.gen_type == 'spoiler':
            return f"This is a {self.preset} spoiler race."

        if self.gen_type == 'mystery':
            return f"The weightset for this race is {self.weightset}."


async def process_league_race(handler, episodeid=None, week=None):
    await handler.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")

    race = await tournament_results.get_active_tournament_race(handler.data.get('name'))
    if race:
        episodeid = race.get('episode_id')
    if race is None and episodeid is None:
        await handler.send_message("Please provide an SG episode ID.")
        return

    try:
        league_race = await LeagueRace.construct(episodeid=episodeid, week=week)
    except Exception as e:
        logging.exception("Problem creating league race.")
        await handler.send_message(f"Could not process league race: {str(e)}")
        return

    teams = league_race.players_by_team

    t = []
    for team in teams:
        t.append(' and '.join([p.data['name'] for p in teams[team]]))

    goal = f"ALTTPR League - {league_race.versus_and_team} - {league_race.friendly_name}"

    await handler.set_raceinfo(f"{goal} - ({'/'.join(league_race.seed.code)})", overwrite=True)

    embed = await league_race.seed.embed(
        name=goal,
        notes=league_race.team_versus,
        emojis=discordbot.emojis
    )

    tournament_embed = await league_race.seed.tournament_embed(
        name=goal,
        notes=league_race.team_versus,
        emojis=discordbot.emojis
    )

    tournament_embed.insert_field_at(
        0, name='RaceTime.gg', value=f"https://racetime.gg{handler.data['url']}", inline=False)
    embed.insert_field_at(
        0, name='RaceTime.gg', value=f"https://racetime.gg{handler.data['url']}", inline=False)

    broadcast_channels = [
        a['name'] for a in league_race.episode['channels'] if not " " in a['name']]

    if len(broadcast_channels) > 0:
        twitch_mode_text = league_race.twitch_mode_command
        twitch_teams_text = f"This race is between {league_race.team_versus}.  Check out rankings for division(s) {', '.join(league_race.division_names)} at {' '.join(league_race.division_urls)}"

        for channel in broadcast_channels:
            await twitch_command_text.insert_command_text(channel.lower(), "mode", twitch_mode_text)
            await twitch_command_text.insert_command_text(channel.lower(), "teams", twitch_teams_text)

        tournament_embed.insert_field_at(
            0, name="Broadcast Channels", value=', '.join([f"[{a}](https://twitch.tv/{a})" for a in broadcast_channels]), inline=False)
        embed.insert_field_at(
            0, name="Broadcast Channels", value=', '.join([f"[{a}](https://twitch.tv/{a})" for a in broadcast_channels]), inline=False)

    audit_channel_id = await config.get(league_race.guild.id, 'AlttprLeagueAuditChannel')
    if audit_channel_id is not None:
        audit_channel = discordbot.get_channel(int(audit_channel_id))
        await audit_channel.send(embed=embed)

    commentary_channel_id = await config.get(
        guild_id=league_race.guild.id,
        parameter='AlttprLeagueCommentaryChannel' if league_race.episode['event'].get(
            'slug', 'invleague') == 'invleague' else 'AlttprLeagueOpenCommChannel'
    )
    commentary_channel = discordbot.get_channel(int(commentary_channel_id))
    if commentary_channel and len(broadcast_channels) > 0:
        await commentary_channel.send(embed=tournament_embed)

    for name, player in league_race.player_discords:
        if player is None:
            await audit_channel.send(f"@here could not send DM to {name}", allowed_mentions=discord.AllowedMentions(everyone=True))
            await handler.send_message(f"Could not send DM to {name}.  Please contact a League Moderator for assistance.")
            continue
        try:
            await player.send(embed=embed)
        except discord.HTTPException:
            if audit_channel is not None:
                await audit_channel.send(f"@here could not send DM to {player.name}#{player.discriminator}", allowed_mentions=discord.AllowedMentions(everyone=True))
                await handler.send_message(f"Could not send DM to {player.name}#{player.discriminator}.  Please contact a League Moderator for assistance.")

    if league_race.gen_type == 'spoiler':
        await spoiler_races.insert_spoiler_race(handler.data.get('name'), league_race.spoiler_log_url, league_race.studyperiod)

    if race is None:
        await tournament_results.insert_tournament_race(
            srl_id=handler.data.get('name'),
            episode_id=league_race.episodeid,
            permalink=league_race.seed.url,
            event='alttprleague_s3',
            week=league_race.week,
            spoiler=league_race.spoiler_log_url if league_race.spoiler_log_url else None
        )
    else:
        await tournament_results.update_tournament_results_rolled(
            srl_id=handler.data.get('name'),
            permalink=league_race.seed.url,
            week=league_race.week,
        )

    await handler.send_message("Seed has been generated, you should have received a DM in Discord.  Please contact a League Moderator if you haven't received the DM.")
    handler.seed_rolled = True


async def process_league_race_start(handler):
    race_id = handler.data.get('name')

    if race_id is None:
        return

    race = await tournament_results.get_active_tournament_race(race_id)

    if race is None:
        return

    if os.environ.get("LEAGUE_SUBMIT_GAME_SECRET"):
        async with aiohttp.request(
            method='get',
            url='https://alttprleague.com/json_ep/submit-game',
            params={
                'slug': race_id,
                'sgl': race['episode_id'],
                'secret': os.environ.get("LEAGUE_SUBMIT_GAME_SECRET")
            }
        ) as _:
            pass
    else:
        print(
            f"Would have reported match {race_id} for episode {race['episode_id']}")

    await tournament_results.update_tournament_results(race_id, status="STARTED")


async def create_league_race_room(episodeid):
    rtgg_alttpr = racetime_bots['alttpr']
    race = await tournament_results.get_active_tournament_race_by_episodeid(episodeid)
    if race:
        async with aiohttp.request(
                method='get',
                url=rtgg_alttpr.http_uri(f"/{race['srl_id']}/data"),
                raise_for_status=True) as resp:
            race_data = json.loads(await resp.read())
        status = race_data.get('status', {}).get('value')
        if not status == 'cancelled':
            return
        await tournament_results.delete_active_tournament_race(race['srl_id'])

    league_race = await LeagueRace.construct(episodeid=episodeid, create_seed=False)

    handler = await rtgg_alttpr.create_race(
        config={
            'goal': '' if league_race.coop else 2,
            'custom_goal': 'Co-op Info Share' if league_race.coop else '',
            'invitational': 'on',
            'info': f"ALTTPR League - {league_race.versus_and_team}",
            'start_delay': 15,
            'time_limit': 24,
            'streaming_required': 'on',
            'allow_comments': 'on',
            'allow_midrace_chat': 'on',
            'chat_message_delay': 0})

    print(handler.data.get('name'))
    await tournament_results.insert_tournament_race(
        srl_id=handler.data.get('name'),
        episode_id=league_race.episodeid,
        event='alttprleague_s3'
    )

    for rtggid in [p.data['rtgg_id'] for p in league_race.players]:
        await handler.invite_user(rtggid)

    embed = discord.Embed(
        title=f"RT.gg Room Opened - {league_race.versus_and_team}",
        description=f"Greetings!  A RaceTime.gg race room has been automatically opened for you.\nYou may access it at https://racetime.gg{handler.data['url']}\n\nEnjoy!",
        color=discord.Colour.blue(),
        timestamp=datetime.datetime.now()
    )

    for name, player in league_race.player_discords:
        if player is None:
            print(f'Could not DM {name}')
            continue
        try:
            await player.send(embed=embed)
        except discord.HTTPException:
            print(f'Could not send room opening DM to {name}')
            continue

    await handler.send_message('Welcome. Use !leaguerace (without any arguments) to roll your seed!  This should be done about 5 minutes prior to the start of you race.  If you need help, ping @Mods in the ALTTPR League Discord.')
    return handler.data


async def is_league_race(name):
    race = await tournament_results.get_active_tournament_race(name)
    if race and race['event'] == 'alttprleague_s3':
        return True
    return False


async def can_gatekeep(rtgg_id):
    guild_id = await config.get(0, 'AlttprLeagueServer')
    guild = discordbot.get_guild(int(guild_id))
    nicknames = await srlnick.get_discord_id_by_rtgg(rtgg_id)

    if not nicknames:
        return False

    discord_user = guild.get_member(nicknames[0]['discord_user_id'])

    if not discord_user:
        return False

    if discord.utils.find(lambda m: m.name in ['Admin', 'Mods', 'Restream Mod', 'Crew Mod', 'Reporting Mod', 'SG Mods', 'Bot Overlord', 'Speedgaming', 'Restreamers'], discord_user.roles):
        return True

    return False
