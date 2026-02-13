import datetime
import json
import logging

import aiohttp
import gspread.exceptions
import gspread_asyncio
import isodate
import pytz
from bs4 import BeautifulSoup

import config
from alttprbot import models
from alttprbot.tournament import test, boots, dailies, smwde, smrl_playoff, nologic, alttprhmg, alttprleague, alttprmini, alttprde, alttpr_quals, alttpr
from alttprbot.tournament import registry_loader
from alttprbot.util import gsheet
from alttprbot_racetime import bot as racetimebot

RACETIME_URL = config.RACETIME_URL

RACETIME_SESSION_TOKEN = config.RACETIME_SESSION_TOKEN
RACETIME_CSRF_TOKEN = config.RACETIME_CSRF_TOKEN

# Phase 0: AVAILABLE_TOURNAMENT_HANDLERS capability catalog
# This represents what handlers exist in the codebase, not what is active.
# Active handlers are determined by TOURNAMENT_DATA (hardcoded fallback)
# or by config/tournaments.yaml when TOURNAMENT_CONFIG_ENABLED is true.
AVAILABLE_TOURNAMENT_HANDLERS = {
    'test': test.TestTournament,
    'alttpr': alttpr_quals.ALTTPRQualifierRace,
    'alttprdaily': dailies.AlttprSGDailyRace,
    'smz3': dailies.SMZ3DailyRace,
    'invleague': alttprleague.ALTTPRLeague,
    'alttprleague': alttprleague.ALTTPROpenLeague,
    'boots': boots.ALTTPRCASBootsTournamentRace,
    'nologic': nologic.ALTTPRNoLogicRace,
    'smwde': smwde.SMWDETournament,
    'alttprhmg': alttprhmg.ALTTPRHMGTournament,
    'alttprmini': alttprmini.ALTTPRMiniTournament,
    'alttprde': alttprde.ALTTPRDETournament,
    'smrl': smrl_playoff.SMRLPlayoffs,
}

# Phase 1: Hardcoded registry fallback (preserved for rollback safety)
# This is the original registry logic, kept as emergency fallback.
# Active when TOURNAMENT_CONFIG_ENABLED is false (default).
if config.DEBUG:
    _HARDCODED_TOURNAMENT_DATA = {
        'test': test.TestTournament
    }
else:
    _HARDCODED_TOURNAMENT_DATA = {
        # REGULAR TOURNAMENTS

        # 'alttprcd': alttprcd.ALTTPRCDTournament,
        # 'alttprde': alttprde.ALTTPRDETournament,
        # 'alttprmini': alttprmini.ALTTPRMiniTournament,
        'alttpr': alttpr_quals.ALTTPRQualifierRace,
        # 'boots': boots.ALTTPRCASBootsTournamentRace,
        # 'nologic': nologic.ALTTPRNoLogicRace,
        # 'smwde': smwde.SMWDETournament,
        # 'alttprfr': alttprfr.ALTTPRFRTournament,
        # 'alttprhmg': alttprhmg.ALTTPRHMGTournament,
        # 'alttpres': alttpres.ALTTPRESTournament,
        # 'smz3coop': smz3coop.SMZ3CoopTournament,
        # 'smbingo': smbingo.SMBingoTournament,
        # 'smrl': smrl_playoff.SMRLPlayoffs,
        # 'sgl24alttpr': alttprsglive.ALTTPRSGLive,

        # Dailies/Weeklies
        'alttprdaily': dailies.AlttprSGDailyRace,
        'smz3': dailies.SMZ3DailyRace,

        # ALTTPR League
        'invleague': alttprleague.ALTTPRLeague,
        'alttprleague': alttprleague.ALTTPROpenLeague,
    }


# Phase 1: Dual-path runtime switch
# Build active registry from config if TOURNAMENT_CONFIG_ENABLED is true,
# otherwise use hardcoded TOURNAMENT_DATA as fallback.
def _initialize_tournament_registry():
    """
    Initialize tournament registry based on TOURNAMENT_CONFIG_ENABLED flag.
    
    If config is enabled, loads from config/tournaments.yaml.
    Otherwise, uses hardcoded TOURNAMENT_DATA as fallback.
    
    Returns active registry and logs source/profile/enabled handlers.
    """
    # Check if config-driven registry is enabled
    config_enabled = getattr(config, 'TOURNAMENT_CONFIG_ENABLED', False)
    
    if config_enabled:
        # Phase 1: Config-backed path
        try:
            # Load and validate configuration
            tournament_config = registry_loader.load_tournament_config(
                available_handlers=AVAILABLE_TOURNAMENT_HANDLERS
            )
            
            # Select profile based on DEBUG flag
            profile_name = 'debug' if config.DEBUG else 'production'
            
            # Build active registry from enabled events
            active_registry = registry_loader.build_active_registry(
                registry=tournament_config,
                available_handlers=AVAILABLE_TOURNAMENT_HANDLERS,
                profile_name=profile_name
            )
            
            # Log summary
            registry_loader.log_registry_summary(
                registry=tournament_config,
                profile_name=profile_name,
                active_registry=active_registry
            )
            
            logging.info(f"Tournament registry loaded from config: profile={profile_name}")
            
            return active_registry
            
        except registry_loader.TournamentConfigError as e:
            # Fatal error: invalid config should fail before operational loops begin
            logging.error(f"FATAL: Tournament config validation failed: {e}")
            logging.error("Tournament loops will not start. Fix config and restart.")
            raise
            
    else:
        # Phase 1: Hardcoded fallback path (default)
        profile_name = 'debug' if config.DEBUG else 'production'
        enabled_events = list(_HARDCODED_TOURNAMENT_DATA.keys())
        
        logging.info(
            f"Tournament Registry: source=hardcoded, profile={profile_name}, "
            f"enabled_events_count={len(enabled_events)}, "
            f"enabled_event_slugs={enabled_events}"
        )
        
        return _HARDCODED_TOURNAMENT_DATA


# Initialize the active tournament registry at module load time
TOURNAMENT_DATA = _initialize_tournament_registry()


async def fetch_tournament_handler(event, episodeid: int, rtgg_handler=None):
    return await TOURNAMENT_DATA[event].construct(episodeid, rtgg_handler)


async def fetch_tournament_handler_v2(event, episode: dict, rtgg_handler=None):
    return await TOURNAMENT_DATA[event].construct_with_episode_data(episode, rtgg_handler)


async def create_tournament_race_room(event, episodeid):
    event_data = await TOURNAMENT_DATA[event].get_config()
    rtgg_bot = racetimebot.racetime_bots[event_data.data.racetime_category]
    race = await models.TournamentResults.get_or_none(episode_id=episodeid)
    if race:
        async with aiohttp.request(method='get', url=rtgg_bot.http_uri(f"/{race.srl_id}/data"),
                                   raise_for_status=True) as resp:
            race_data = json.loads(await resp.read())
        status = race_data.get('status', {}).get('value')
        if not status == 'cancelled':
            return
        await race.delete()

    handler = await TOURNAMENT_DATA[event].construct_race_room(episodeid)
    return handler


async def race_recording_task():
    agcm = gspread_asyncio.AsyncioGspreadClientManager(gsheet.get_creds)
    agc = await agcm.authorize()

    for event, event_obj in TOURNAMENT_DATA.items():
        event_data = await event_obj.get_config()
        if event_data.data.gsheet_id is None:
            continue

        wb = await agc.open_by_key(event_data.data.gsheet_id)

        races = await models.TournamentResults.filter(written_to_gsheet=None, event=event)

        if not races:
            continue

        try:
            wks = await wb.worksheet(event)
        except gspread.exceptions.WorksheetNotFound:
            wks = await wb.add_worksheet(event, 50, 10)
            await wks.append_row(values=[
                'episode',
                'start time (eastern)',
                'racetime',
                'winner',
                'loser',
                'winner finish',
                'loser finish',
                'permalink',
                'spoiler',
            ])

        for race in races:
            logging.info(f"Recording {race.episode_id} for {event} to {event_data.data.gsheet_id}")
            try:
                async with aiohttp.request(
                        method='get',
                        url=f"{RACETIME_URL}/{race.srl_id}/data",
                        raise_for_status=True) as resp:
                    race_data = json.loads(await resp.read())

                if race_data['status']['value'] == 'finished':
                    winner = [e for e in race_data['entrants'] if e['place'] == 1][
                        0]  # pylint: disable=used-before-assignment
                    runnerup = [e for e in race_data['entrants'] if e['place'] in [2, None]][
                        0]  # pylint: disable=used-before-assignment

                    started_at = isodate.parse_datetime(race_data['started_at']).astimezone(pytz.timezone('US/Eastern'))
                    ended_at = isodate.parse_datetime(race_data['ended_at'])
                    record_at = ended_at + datetime.timedelta(minutes=event_data.data.stream_delay)

                    if record_at > datetime.datetime.now(tz=datetime.timezone.utc):
                        continue

                    await wks.append_row(values=[
                        race.episode_id,
                        started_at.strftime("%Y-%m-%d %H:%M:%S"),
                        f"{RACETIME_URL}/{race.srl_id}",
                        winner['user']['name'],
                        runnerup['user']['name'],
                        str(isodate.parse_duration(winner['finish_time'])) if isinstance(winner['finish_time'],
                                                                                         str) else None,
                        str(isodate.parse_duration(runnerup['finish_time'])) if isinstance(runnerup['finish_time'],
                                                                                           str) else None,
                        race.permalink,
                        race.spoiler
                    ])
                    race.status = "RECORDED"
                    race.written_to_gsheet = 1
                    await race.save()

                    if event_data.data.auto_record:
                        await racetime_auto_record(race_data)

                elif race_data['status']['value'] == 'cancelled':
                    await race.delete()
                else:
                    continue
            except Exception as e:
                logging.exception("Encountered a problem when attempting to record a race.")

    logging.debug('done')


async def racetime_auto_record(race_data):
    url = RACETIME_URL + race_data['url']
    record_url = url + "/monitor/record"
    recorded = race_data.get('recorded', True)
    recordable = race_data.get('recordable', False)

    if recorded or not recordable:
        return

    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(
                    method='get',
                    url=url,
                    cookies={'sessionid': RACETIME_SESSION_TOKEN,
                             'csrftoken': RACETIME_CSRF_TOKEN},
                    raise_for_status=True
            ) as resp:
                soup = BeautifulSoup(await resp.text(), features="html5lib")
        except Exception as e:
            raise Exception("Unable to acquire CSRF token.  Please contact Synack for help.") from e

        csrftoken = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
        data = {'csrfmiddlewaretoken': csrftoken}

        try:
            async with aiohttp.request(
                    method='post',
                    url=record_url,
                    cookies={'sessionid': RACETIME_SESSION_TOKEN,
                             'csrftoken': RACETIME_CSRF_TOKEN},
                    headers={'Origin': RACETIME_URL,
                             'Referer': url},
                    data=data,
                    raise_for_status=True
            ) as resp:
                pass
        except Exception:
            logging.exception("Unable to automatically record race. Skipping...")
