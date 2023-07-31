import datetime
import json
import logging
import os

import aiohttp
from bs4 import BeautifulSoup
import gspread_asyncio
import gspread.exceptions
import isodate
import pytz
from alttprbot_racetime import bot as racetimebot

from alttprbot import models
from alttprbot.tournament import test, boots, alttprde, alttprmini, dailies, smwde, smrl_playoff, alttpr, alttprhmg
from alttprbot.util import gsheet
from config import Config as c

RACETIME_URL = os.environ.get('RACETIME_URL', 'https://racetime.gg')

RACETIME_SESSION_TOKEN = os.environ.get('RACETIME_SESSION_TOKEN')
RACETIME_CSRF_TOKEN = os.environ.get('RACETIME_CSRF_TOKEN')

if c.DEBUG:
    TOURNAMENT_DATA = {
        'test': test.TestTournament
    }
else:
    TOURNAMENT_DATA = {
        # REGULAR TOURNEMNTS

        # 'alttprcd': alttprcd.ALTTPRCDTournament,
        # 'alttprde': alttprde.ALTTPRDETournamentBrackets,
        'alttprmini': alttprmini.ALTTPRMiniTournament,
        'alttpr': alttpr.ALTTPR2023Race,
        'boots': boots.ALTTPRCASBootsTournamentRace,
        # 'nologic': nologic.ALTTPRNoLogicRace,
        'smwde': smwde.SMWDETournament,
        # 'alttprfr': alttprfr.ALTTPRFRTournament,
        'alttprhmg': alttprhmg.ALTTPRHMGTournament,
        # 'alttpres': alttpres.ALTTPRESTournament,
        # 'smz3coop': smz3coop.SMZ3CoopTournament,
        # 'smbingo': smbingo.SMBingoTournament,
        'smrl': smrl_playoff.SMRLPlayoffs,

        # Dailies/Weeklies
        'alttprdaily': dailies.AlttprSGDailyRace,
        'smz3': dailies.SMZ3DailyRace,

        # ALTTPR League
        # 'invleague': alttprleague.ALTTPRLeague,
        # 'alttprleague': alttprleague.ALTTPROpenLeague,
    }


async def fetch_tournament_handler(event, episodeid: int, rtgg_handler=None):
    return await TOURNAMENT_DATA[event].construct(episodeid, rtgg_handler)


async def fetch_tournament_handler_v2(event, episode: dict, rtgg_handler=None):
    return await TOURNAMENT_DATA[event].construct_with_episode_data(episode, rtgg_handler)


async def create_tournament_race_room(event, episodeid):
    event_data = await TOURNAMENT_DATA[event].get_config()
    rtgg_bot = racetimebot.racetime_bots[event_data.data.racetime_category]
    race = await models.TournamentResults.get_or_none(episode_id=episodeid)
    if race:
        async with aiohttp.request(method='get', url=rtgg_bot.http_uri(f"/{race.srl_id}/data"), raise_for_status=True) as resp:
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
                    winner = [e for e in race_data['entrants'] if e['place'] == 1][0]  # pylint: disable=used-before-assignment
                    runnerup = [e for e in race_data['entrants'] if e['place'] in [2, None]][0]  # pylint: disable=used-before-assignment

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
                        str(isodate.parse_duration(winner['finish_time'])) if isinstance(winner['finish_time'], str) else None,
                        str(isodate.parse_duration(runnerup['finish_time'])) if isinstance(runnerup['finish_time'], str) else None,
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
