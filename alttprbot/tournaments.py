import json
import logging
import os
from dataclasses import dataclass

import aiohttp
import discord
import gspread_asyncio
import isodate
import pytz
from alttprbot_discord.bot import discordbot
from alttprbot_racetime.bot import racetime_bots

from alttprbot import models
from alttprbot.tournament import core, alttpr, alttprcd, alttpres, alttprfr, alttprhmg, smz3coop
from alttprbot.util import gsheet
from config import Config as c

TOURNAMENT_RESULTS_SHEET = os.environ.get('TOURNAMENT_RESULTS_SHEET', None)
RACETIME_URL = os.environ.get('RACETIME_URL', 'https://racetime.gg')

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

    scheduling_needs_tracker = False

    admin_roles: list = None
    helper_roles: list = None
    commentator_roles: list = None
    mod_roles: list = None

    lang: str = 'en'
    submission_form: list = []
    coop: bool = False

    tournament_class: core.TournamentRace = core.TournamentRace

TOURNAMENT_DATA = {}

if c.DEBUG:
    test_guild = discordbot.get_guild(508335685044928540)
    TOURNAMENT_DATA['test'] = TournamentConfig(
        guild=test_guild,
        racetime_category='alttpr',
        racetime_goal='Beat the game',
        event_slug="test",
        audit_channel=discordbot.get_channel(537469084527230976),
        commentary_channel=discordbot.get_channel(659307060499972096),
        helper_roles=[
            test_guild.get_role(523276397679083520),
        ],
        lang='en',
        tournament_class=alttpr.ALTTPRTournamentRace
    )
else:
    alttpr_de_guild = discordbot.get_guild(469300113290821632)
    TOURNAMENT_DATA['alttprcd'] = TournamentConfig(
        guild=alttpr_de_guild,
        racetime_category='alttpr',
        racetime_goal='Beat the game',
        event_slug="alttprcd",
        audit_channel=discordbot.get_channel(473668481011679234),
        commentary_channel=discordbot.get_channel(469317757331308555),
        helper_roles=[
            alttpr_de_guild.get_role(534030648713674765),
            alttpr_de_guild.get_role(469300493542490112),
            alttpr_de_guild.get_role(623071415129866240),
        ],
        lang='de',
        tournament_class=alttprcd.ALTTPRCDTournament
    )

    alttpr_tournament_guild = discordbot.get_guild(334795604918272012)
    TOURNAMENT_DATA['alttpr'] = TournamentConfig(
        guild=alttpr_tournament_guild,
        racetime_category='alttpr',
        racetime_goal='Beat the game',
        event_slug="alttpr",
        audit_channel=discordbot.get_channel(647966639266201620),
        commentary_channel=discordbot.get_channel(408347983709470741),
        scheduling_needs_channel=discordbot.get_channel(434560353461075969),
        scheduling_needs_tracker=True,
        helper_roles=[
            alttpr_tournament_guild.get_role(334797023054397450),
            alttpr_tournament_guild.get_role(435200206552694794),
            alttpr_tournament_guild.get_role(482353483853332481),
            alttpr_tournament_guild.get_role(426487540829388805),
            alttpr_tournament_guild.get_role(613394561594687499),
            alttpr_tournament_guild.get_role(334796844750209024)
        ],
        tournament_class=alttpr.ALTTPRTournamentRace
    )

    smwde_guild = discordbot.get_guild(753727862229565612)
    TOURNAMENT_DATA['smwde'] = TournamentConfig(
        guild=smwde_guild,
        racetime_category='smw-hacks',
        racetime_goal='Any%',
        event_slug="smwde",
        audit_channel=discordbot.get_channel(826775494329499648),
        scheduling_needs_channel=discordbot.get_channel(835946387065012275),
        helper_roles=[
            smwde_guild.get_role(754845429773893782),
            smwde_guild.get_role(753742980820631562),
        ],
        lang='de',
        tournament_class=core.TournamentRace
    )

    alttprfr_guild = discordbot.get_guild(470200169841950741)
    TOURNAMENT_DATA['alttprfr'] = TournamentConfig(
        guild=alttprfr_guild,
        racetime_category='alttpr',
        racetime_goal='Beat the game',
        event_slug="alttprfr",
        audit_channel=discordbot.get_channel(856581631241486346),
        commentary_channel=discordbot.get_channel(470202208261111818),
        helper_roles=[
            alttprfr_guild.get_role(482266765137805333),
            alttprfr_guild.get_role(507932829527703554),
        ],
        lang='fr',
        tournament_class=alttprfr.ALTTPRFRTournament,
        submission_form=[
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
    )

    alttprhmg_guild = discordbot.get_guild(535946014037901333)
    TOURNAMENT_DATA['alttprhmg'] = TournamentConfig(
        guild=alttprhmg_guild,
        racetime_category='alttpr',
        racetime_goal='Beat the game (glitched)',
        event_slug="alttprhmg",
        audit_channel=discordbot.get_channel(647966639266201620),
        commentary_channel=discordbot.get_channel(408347983709470741),
        scheduling_needs_channel=discordbot.get_channel(434560353461075969),
        scheduling_needs_tracker=True,
        helper_roles=[
            alttprhmg_guild.get_role(549708578731327489),
            alttprhmg_guild.get_role(535962854004883467),
            alttprhmg_guild.get_role(535962802230132737),
        ],
        tournament_class=alttprhmg.ALTTPRHMGTournament,
    )

    alttpres_guild = discordbot.get_guild(477850508368019486)
    TOURNAMENT_DATA['alttpres'] = TournamentConfig(
        guild=alttpres_guild,
        racetime_category='alttpr',
        racetime_goal='Beat the game',
        event_slug="alttpres",
        audit_channel=discordbot.get_channel(859058002426462211),
        commentary_channel=discordbot.get_channel(838011943000080395),
        scheduling_needs_channel=discordbot.get_channel(863771537903714324),
        scheduling_needs_tracker=True,
        helper_roles=[
            alttpres_guild.get_role(479423657584754698),
            alttpres_guild.get_role(477968190606016528),
        ],
        lang="es",
        tournament_class=alttpres.ALTTPRESTournament,
        submission_form=[
            {
                'key': 'preset',
                'label': 'Preset',
                'settings': {
                    'ambrosia': 'Ambrosia',
                    'casualboots': 'Casual Boots',
                    'mcs': 'Maps, Compasses, and Small Keys',
                    'open': 'Open',
                    'standard': 'Standard',
                    'adkeys': "All Dungeons + Keysanity (Round of 8 only)",
                    'dungeons': 'All Dungeons (Round of 8 only)',
                    'keysanity': 'Keysanity (Round of 8 only)',
                }
            }
        ]
    )

    smz3_tournament = discordbot.get_guild(460905692857892865)
    TOURNAMENT_DATA['smz3coop'] = TournamentConfig(
        guild=smz3_tournament,
        racetime_category='smz3',
        racetime_goal='Beat the games',
        event_slug="smz3coop",
        audit_channel=discordbot.get_channel(516808047935619073),
        commentary_channel=discordbot.get_channel(687471466714890296),
        scheduling_needs_channel=discordbot.get_channel(864249492370489404),
        scheduling_needs_tracker=True,
        helper_roles=[
            smz3_tournament.get_role(464497534631542795),
        ],
        tournament_class=smz3coop.SMZ3CoopTournament,
    )

async def fetch_tournament_handler(event, episodeid: int, rtgg_handler=None):
    tournament_class = TOURNAMENT_DATA[event].tournament_class
    return await tournament_class.construct(TOURNAMENT_DATA[event], episodeid, rtgg_handler)

async def create_tournament_race_room(event, episodeid):
    event_data: TournamentConfig = TOURNAMENT_DATA[event]
    rtgg_bot = racetime_bots[event_data.racetime_category]
    race = await models.TournamentResults.get_or_none(episode_id=episodeid)
    if race:
        async with aiohttp.request(method='get', url=rtgg_bot.http_uri(f"/{race.srl_id}/data"), raise_for_status=True) as resp:
            race_data = json.loads(await resp.read())
        status = race_data.get('status', {}).get('value')
        if not status == 'cancelled':
            return
        await race.delete()

    handler = await event_data.tournament_class.construct_race_room(event_data, episodeid)
    return handler

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
