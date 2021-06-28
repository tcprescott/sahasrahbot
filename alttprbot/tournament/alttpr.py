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
from alttprbot.database import (tournament_results, srlnick, tournaments, tournament_games)
from alttprbot import models
from alttprbot.util import gsheet, speedgaming
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.bot import discordbot
from alttprbot_discord.util import alttpr_discord
from alttprbot_racetime import bot as racetime

TOURNAMENT_RESULTS_SHEET = os.environ.get('TOURNAMENT_RESULTS_SHEET', None)
RACETIME_URL = os.environ.get('RACETIME_URL', 'https://racetime.gg')
APP_URL = os.environ.get('APP_URL', 'https://sahasrahbotapi.synack.live')

SETTINGSMAP = {
    'Defeat Ganon': 'ganon',
    'Fast Ganon': 'fast_ganon',
    'All Dungeons': 'dungeons',
    'Pedestal': 'pedestal',
    'Standard': 'standard',
    'Open': 'open',
    'Inverted': 'inverted',
    'Retro': 'retro',
    'Randomized': 'randomized',
    'Assured': 'assured',
    'Vanilla': 'vanilla',
    'Swordless': 'swordless',
    'Shuffled': 'shuffled',
    'Full': 'full',
    'Random': 'random',
    'Hard': 'hard',
    'Normal': 'normal',
    'Off': 'off',
    'On': 'on',
    'None': 'none'
}

ALTTPR_FR_SETTINGS_LIST = [
    {
        'key': 'dungeon_items',
        'label': 'Dungeon Item Shuffle',
        'settings': {
            'standard': 'Standard',
            'mc': 'Maps and Compasses',
            'mcs': 'Maps, Compasses, and Small Keys',
            'full': 'Keysanity',
        }
    },
    {
        'key': 'goal',
        'label': 'Goal',
        'settings': {
            'ganon': 'Defeat Ganon',
            'fast_ganon': 'Fast Ganon',
        }
    },
    {
        'key': 'world_state',
        'label': 'World State',
        'settings': {
            'open': 'Open',
            'standard': 'Standard',
            'inverted': 'Inverted',
            'retro': 'Retro',
        }
    },
    {
        'key': 'boss_shuffle',
        'label': 'Boss Shuffle',
        'settings': {
            'none': 'Off',
            'random': 'Random'
        }
    },
    {
        'key': 'enemy_shuffle',
        'label': 'Enemy Shuffle',
        'settings': {
            'none': 'Off',
            'shuffled': 'Shuffled'
        }
    },
    {
        'key': 'hints',
        'label': 'Hints',
        'settings': {
            'off': 'Off',
            'on': 'On'
        }
    },
    {
        'key': 'swords',
        'label': 'Swords',
        'settings': {
            'randomized': 'Randomized',
            'assured': 'Assured',
            'vanilla': 'Vanilla',
            'swordless': 'Swordless',
        }
    },
    {
        'key': 'item_pool',
        'label': 'Item Pool',
        'settings': {
            'normal': 'Normal',
            'hard': 'Hard'
        }
    },
    {
        'key': 'item_functionality',
        'label': 'Item Functionality',
        'settings': {
            'normal': 'Normal',
            'hard': 'Hard'
        }
    },
]

ALTTPR_ES_SETTINGS_LIST = [
    {
        'key': 'preset',
        'label': 'Preset',
        'settings': {
            'ambrosia': 'Ambrosia',
            'casualboots': 'Casual Boots',
            'mcs': 'Maps, Compasses, and Small Keys',
            'open': 'Open',
            'standard': 'Standard',
            'dungeons': 'All Dungeons (Round of 8 only)',
            'keysanity': 'Keysanity (Round of 8 only)',
        }
    }
]

class UnableToLookupUserException(SahasrahBotException):
    pass


class UnableToLookupEpisodeException(SahasrahBotException):
    pass


class TournamentPlayer():
    def __init__(self):
        pass

    @classmethod
    async def construct(cls, discord_id: int, guild):
        playerobj = cls()

        result = await srlnick.get_nickname(discord_id)
        playerobj.data = result
        playerobj.discord_user = guild.get_member(result['discord_user_id'])
        playerobj.name = playerobj.discord_user.name

        return playerobj

    @classmethod
    async def construct_discord_name(cls, discord_name: str, guild):
        playerobj = cls()

        playerobj.discord_user = guild.get_member_named(discord_name)
        playerobj.name = discord_name
        result = await srlnick.get_nickname(playerobj.discord_user.id)
        playerobj.data = result

        return playerobj


class TournamentRace():
    def __init__(self, episodeid: int):
        self.episodeid = int(episodeid)
        self.players = []

    @classmethod
    async def construct(cls, episodeid):
        tournament_race = cls(episodeid)
        await discordbot.wait_until_ready()
        await tournament_race.update_data()
        return tournament_race

    async def update_data(self):
        self.episode = await speedgaming.get_episode(self.episodeid)

        self.data = await tournaments.get_tournament(self.episode['event']['slug'])

        if self.data is None:
            raise UnableToLookupEpisodeException('SG Episode ID not a recognized event.  This should not have happened.')

        self.guild = discordbot.get_guild(self.data['guild_id'])

        self.players = []
        for player in self.episode['match1']['players']:
            # first try a more concrete match of using the discord id cached by SG
            looked_up_player = await self.make_tournament_player(player)
            self.players.append(looked_up_player)

        self.bracket_settings = await tournament_games.get_game_by_episodeid_submitted(self.episodeid)

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
        method = 'roll_' + self.event_slug
        if hasattr(self, method):
            await getattr(self, method)()

    # handle rolling for alttprcd tournament (German)
    async def roll_alttprcd(self):
        self.seed, self.preset_dict = await preset.get_preset('crossedkeydrop')

    # handle rolling for francophone alttpr tournament
    async def roll_alttprfr(self):
        if self.bracket_settings is None:
            raise Exception('Missing bracket settings.  Please submit!')

        self.preset_dict = None
        self.seed = await alttpr_discord.ALTTPRDiscord.generate(
            settings=json.loads(self.bracket_settings['settings'])
        )

    async def roll_alttprhmg(self):
        self.seed, self.preset_dict = await preset.get_preset('hybridmg')

    async def roll_alttpres(self):
        self.seed, self.preset_dict = await preset.get_preset('open')

    # test
    async def roll_test(self):
        if self.bracket_settings is None:
            raise Exception('Missing bracket settings.  Please submit!')

        self.preset_dict = None
        self.seed = await alttpr_discord.ALTTPRDiscord.generate(
            settings=json.loads(self.bracket_settings['settings'])
        )

    # handle rolling for alttpr main tournament
    async def roll_alttpr(self):
        self.seed, self.preset_dict = await preset.get_preset('tournament', nohints=True, allow_quickswap=True)

    @property
    def submit_link(self):
        return f"{APP_URL}/submit/{self.event_slug}?episode_id={self.episodeid}"

    @property
    def game_number(self):
        if self.bracket_settings:
            return self.bracket_settings.get('game_number', None)
        return None

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
        return ' vs. '.join(self.player_names)

    @property
    def player_discords(self):
        return [(p.name, p.discord_user) for p in self.players]

    @property
    def player_racetime_ids(self):
        return [p.data['rtgg_id'] for p in self.players]

    @property
    def player_names(self):
        return [p.name for p in self.players]

    @property
    def broadcast_channels(self):
        return [a['name'] for a in self.episode['channels'] if not " " in a['name']]


async def process_tournament_race(handler, episodeid=None):
    await handler.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")

    race = await tournament_results.get_active_tournament_race(handler.data.get('name'))
    if isinstance(handler.tournament, TournamentRace):
        tournament_race = handler.tournament
        await tournament_race.update_data()
    else:
        if race:
            episodeid = race.get('episode_id')
        if race is None and episodeid is None:
            await handler.send_message("Please provide an SG episode ID.")
            return

        try:
            tournament_race = await TournamentRace.construct(episodeid=episodeid)
        except Exception as e:
            logging.exception("Problem creating tournament race.")
            await handler.send_message(f"Could not process tournament race: {str(e)}")
            return

    await tournament_race.roll()

    if tournament_race.bracket_settings:
        goal = f"{tournament_race.event_name} - {tournament_race.versus} - Game #{tournament_race.game_number}"
    else:
        goal = f"{tournament_race.event_name} - {tournament_race.versus} - {tournament_race.friendly_name}"

    embed = await tournament_race.seed.embed(
        name=goal,
        notes=tournament_race.versus,
        emojis=discordbot.emojis
    )

    tournament_embed = await tournament_race.seed.tournament_embed(
        name=goal,
        notes=tournament_race.versus,
        emojis=discordbot.emojis
    )

    goal += f" - ({'/'.join(tournament_race.seed.code)})"

    tournament_embed.insert_field_at(
        0, name='RaceTime.gg', value=handler.bot.http_uri(handler.data['url']), inline=False)
    embed.insert_field_at(
        0, name='RaceTime.gg', value=handler.bot.http_uri(handler.data['url']), inline=False)

    if broadcast_channels := tournament_race.broadcast_channels:
        tournament_embed.insert_field_at(
            0, name="Broadcast Channels", value=', '.join([f"[{a}](https://twitch.tv/{a})" for a in broadcast_channels]), inline=False)
        embed.insert_field_at(
            0, name="Broadcast Channels", value=', '.join([f"[{a}](https://twitch.tv/{a})" for a in broadcast_channels]), inline=False)

        goal += f" - Restream(s) at {', '.join(broadcast_channels)}"

    await handler.set_raceinfo(goal, overwrite=True)

    audit_channel_id = tournament_race.data['audit_channel_id']
    if audit_channel_id is not None:
        audit_channel = discordbot.get_channel(audit_channel_id)
        await audit_channel.send(embed=embed)
    else:
        audit_channel = None

    commentary_channel_id = tournament_race.data['commentary_channel_id']
    if commentary_channel_id is not None:
        commentary_channel = discordbot.get_channel(int(commentary_channel_id))
        if commentary_channel and len(broadcast_channels) > 0:
            await commentary_channel.send(embed=tournament_embed)

    for name, player in tournament_race.player_discords:
        if player is None:
            await audit_channel.send(f"@here could not send DM to {name}", allowed_mentions=discord.AllowedMentions(everyone=True))
            await handler.send_message(f"Could not send DM to {name}.  Please contact a Tournament Moderator for assistance.")
            continue
        try:
            await player.send(embed=embed)
        except discord.HTTPException:
            if audit_channel is not None:
                await audit_channel.send(f"@here could not send DM to {player.name}#{player.discriminator}", allowed_mentions=discord.AllowedMentions(everyone=True))
                await handler.send_message(f"Could not send DM to {player.name}#{player.discriminator}.  Please contact a Tournament Moderator for assistance.")

    if race is None:
        await tournament_results.insert_tournament_race(
            srl_id=handler.data.get('name'),
            episode_id=tournament_race.episodeid,
            permalink=tournament_race.seed.url,
            event=tournament_race.event_slug,
            spoiler=None
        )
    else:
        await tournament_results.update_tournament_results_rolled(
            srl_id=handler.data.get('name'),
            permalink=tournament_race.seed.url
        )

    await handler.send_message("Seed has been generated, you should have received a DM in Discord.  Please contact a Tournament Moderator if you haven't received the DM.")
    handler.seed_rolled = True


async def process_tournament_race_start(handler):
    race_id = handler.data.get('name')

    if race_id is None:
        return

    race = await tournament_results.get_active_tournament_race(race_id)

    if race is None:
        return

    await tournament_results.update_tournament_results(race_id, status="STARTED")


async def create_tournament_race_room(episodeid, category='alttpr', goal='Beat the game'):
    rtgg_alttpr = racetime.racetime_bots[category]
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

    tournament_race = await TournamentRace.construct(episodeid=episodeid)

    handler = await rtgg_alttpr.startrace(
        goal=goal,
        invitational=True,
        unlisted=False,
        info=f"{tournament_race.event_name} - {tournament_race.versus}",
        start_delay=15,
        time_limit=24,
        streaming_required=True,
        auto_start=True,
        allow_comments=True,
        hide_comments=True,
        allow_prerace_chat=True,
        allow_midrace_chat=True,
        allow_non_entrant_chat=False,
        chat_message_delay=0
    )

    handler.tournament = tournament_race

    logging.info(handler.data.get('name'))
    await tournament_results.insert_tournament_race(
        srl_id=handler.data.get('name'),
        episode_id=tournament_race.episodeid,
        event=tournament_race.event_slug
    )

    for rtggid in tournament_race.player_racetime_ids:
        await handler.invite_user(rtggid)

    embed = discord.Embed(
        title=f"RT.gg Room Opened - {tournament_race.versus}",
        description=f"Greetings!  A RaceTime.gg race room has been automatically opened for you.\nYou may access it at {handler.bot.http_uri(handler.data['url'])}\n\nEnjoy!",
        color=discord.Colour.blue(),
        timestamp=datetime.datetime.now()
    )

    for name, player in tournament_race.player_discords:
        if player is None:
            logging.info(f'Could not DM {name}')
            continue
        try:
            await player.send(embed=embed)
        except discord.HTTPException:
            logging.info(f'Could not send room opening DM to {name}')
            continue

    if category != 'smw-hacks':
        await handler.send_message('Welcome. Use !tournamentrace (without any arguments) to roll your seed!  This should be done about 5 minutes prior to the start of your race.')

    return handler.data


async def alttprfr_process_settings_form(payload):
    episode_id = int(payload['episodeid'])

    tournament_race = await TournamentRace.construct(episodeid=episode_id)

    embed = discord.Embed(
        title=f"ALTTPR FR - {tournament_race.versus}",
        description='Thank you for submitting your settings for this race!  Below is what will be played.\nIf this is incorrect, please contact a tournament admin.',
        color=discord.Colour.blue()
    )

    settings = {
        "glitches": "none",
        "item_placement": "advanced",
        "dungeon_items": payload.get("dungeon_items", "standard"),
        "accessibility": "items",
        "goal": payload.get("goal", "ganon"),
        "crystals": {
            "ganon": "7",
            "tower": "7"
        },
        "mode": payload.get("world_state", "mode"),
        "entrances": "none",
        "hints": payload.get("hints", "off"),
        "weapons": payload.get("swords", "randomized"),
        "item": {
            "pool": payload.get("item_pool", "normal"),
            "functionality": payload.get("item_functionality", "normal"),
        },
        "tournament": True,
        "spoilers": "off",
        "lang": "en",
        "enemizer": {
            "boss_shuffle": payload.get("boss_shuffle", "none"),
            "enemy_shuffle": payload.get("enemy_shuffle", "none"),
            "enemy_damage": "default",
            "enemy_health": "default",
            "pot_shuffle": "off"
        },
        "allow_quickswap": True
    }

    if settings['enemizer']['enemy_shuffle'] != "none" and settings['mode'] == 'standard':
        settings['weapons'] = 'assured'

    settings_formatted = ""
    for setting in ALTTPR_FR_SETTINGS_LIST:
        settings_formatted += f"**{setting['label']}:** {setting['settings'][payload.get(setting['key'])]}\n"

    embed.add_field(name="Settings", value=settings_formatted)

    await models.TournamentGames.update_or_create(episode_id=episode_id, defaults={'settings': settings, 'event': 'alttprfr'})

    audit_channel_id = tournament_race.data['audit_channel_id']
    if audit_channel_id is not None:
        audit_channel = discordbot.get_channel(audit_channel_id)
        await audit_channel.send(embed=embed)
    else:
        audit_channel = None

    for name, player in tournament_race.player_discords:
        if player is None:
            await audit_channel.send(f"@here could not send DM to {name}", allowed_mentions=discord.AllowedMentions(everyone=True), embed=embed)
            continue
        try:
            await player.send(embed=embed)
        except discord.HTTPException:
            if audit_channel is not None:
                await audit_channel.send(f"@here could not send DM to {player.name}#{player.discriminator}", allowed_mentions=discord.AllowedMentions(everyone=True), embed=embed)

    return tournament_race

async def alttpres_process_settings_form(payload):
    episode_id = int(payload['episodeid'])

    tournament_race = await TournamentRace.construct(episodeid=episode_id)

    embed = discord.Embed(
        title=f"ALTTPR ES - {tournament_race.versus}",
        description='Thank you for submitting your settings for this race!  Below is what will be played.\nIf this is incorrect, please contact a tournament admin.',
        color=discord.Colour.blue()
    )

    preset_dict = await preset.fetch_preset(payload['preset'])

    preset_dict['tournament'] = True
    preset_dict['allow_quickswap'] = True
    preset_dict['spoilers'] = 'off'

    embed.add_field(name="Preset", value=payload['preset'])

    await models.TournamentGames.update_or_create(episode_id=episode_id, defaults={'settings': preset_dict['settings'], 'event': 'alttpres'})

    audit_channel_id = tournament_race.data['audit_channel_id']
    if audit_channel_id is not None:
        audit_channel = discordbot.get_channel(audit_channel_id)
        await audit_channel.send(embed=embed)
    else:
        audit_channel = None

    for name, player in tournament_race.player_discords:
        if player is None:
            await audit_channel.send(f"@here could not send DM to {name}", allowed_mentions=discord.AllowedMentions(everyone=True), embed=embed)
            continue
        try:
            await player.send(embed=embed)
        except discord.HTTPException:
            if audit_channel is not None:
                await audit_channel.send(f"@here could not send DM to {player.name}#{player.discriminator}", allowed_mentions=discord.AllowedMentions(everyone=True), embed=embed)

    return tournament_race

async def is_tournament_race(name):
    race = await tournament_results.get_active_tournament_race(name)
    if race:
        return True
    return False


async def can_gatekeep(rtgg_id, name):
    race = await tournament_results.get_active_tournament_race(name)

    tournament = await tournaments.get_tournament(race['event'])
    if tournament is None:
        return False
    guild = discordbot.get_guild(tournament['guild_id'])
    nicknames = await srlnick.get_discord_id_by_rtgg(rtgg_id)

    if not nicknames:
        return False

    discord_user = guild.get_member(nicknames[0]['discord_user_id'])

    if not discord_user:
        return False

    if helper_roles := tournament.get('helper_roles', None):
        if discord.utils.find(lambda m: m.name in helper_roles.split(','), discord_user.roles):
            return True

    return False


async def race_recording_task():
    if TOURNAMENT_RESULTS_SHEET is None:
        return

    races = await tournament_results.get_unrecorded_races()
    if races is None:
        return

    agcm = gspread_asyncio.AsyncioGspreadClientManager(gsheet.get_creds)
    agc = await agcm.authorize()
    wb = await agc.open_by_key(TOURNAMENT_RESULTS_SHEET)

    for race in races:
        logging.info(f"Recording {race['episode_id']}")
        try:

            sheet_name = race['event']
            wks = await wb.worksheet(sheet_name)

            async with aiohttp.request(
                    method='get',
                    url=f"{RACETIME_URL}/{race['srl_id']}/data",
                    raise_for_status=True) as resp:
                race_data = json.loads(await resp.read())

            if race_data['status']['value'] == 'finished':
                winner = [e for e in race_data['entrants'] if e['place'] == 1][0]
                runnerup = [e for e in race_data['entrants'] if e['place'] in [2, None]][0]

                started_at = isodate.parse_datetime(race_data['started_at']).astimezone(pytz.timezone('US/Eastern'))
                await wks.append_row(values=[
                    race['episode_id'],
                    started_at.strftime("%Y-%m-%d %H:%M:%S"),
                    f"{RACETIME_URL}/{race['srl_id']}",
                    winner['user']['name'],
                    runnerup['user']['name'],
                    str(isodate.parse_duration(winner['finish_time'])) if isinstance(winner['finish_time'], str) else None,
                    str(isodate.parse_duration(runnerup['finish_time'])) if isinstance(runnerup['finish_time'], str) else None,
                    race['permalink'],
                    race['spoiler']
                ])
                await tournament_results.update_tournament_race_status(race['srl_id'], "RECORDED")
                await tournament_results.mark_as_written(race['srl_id'])
            elif race_data['status']['value'] == 'cancelled':
                await tournament_results.delete_active_tournament_race_all(race['srl_id'])
            else:
                continue
        except Exception as e:
            logging.exception("Encountered a problem when attempting to record a race.")

    logging.debug('done')

async def send_race_submission_form(episodeid):
    tournament_race = await TournamentRace.construct(episodeid=episodeid)
    if tournament_race.bracket_settings is not None:
        return

    msg = (
        f"Greetings!  Do not forget to submit settings for your upcoming race: `{tournament_race.versus}`!\n\n"
        f"For your convenience, you visit {tournament_race.submit_link} to submit the settings.\n\n"
    )

    for name, player in tournament_race.player_discords:
        if player is None:
            continue
        logging.info(f"Sending league playoff submit reminder to {name}.")
        await player.send(msg)

    await models.TournamentGames.update_or_create(episode_id=episodeid, defaults={'event': tournament_race.event_slug, 'submitted': 1})