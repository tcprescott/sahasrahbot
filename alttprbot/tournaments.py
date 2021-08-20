import json
import logging
import os

import aiohttp
import gspread_asyncio
import gspread.exceptions
import isodate
import pytz
from alttprbot_racetime.bot import racetime_bots

from alttprbot import models
from alttprbot.tournament import (test, alttpr, alttprcd, alttpres, alttprfr, # pylint: disable=unused-import
    alttprhmg, smwde, smz3coop, smbingo, smz3, alttprdaily, alttprleague) # pylint: disable=unused-import
from alttprbot.util import gsheet
from config import Config as c

TOURNAMENT_RESULTS_SHEET = os.environ.get('TOURNAMENT_RESULTS_SHEET', None)
RACETIME_URL = os.environ.get('RACETIME_URL', 'https://racetime.gg')

if c.DEBUG:
    TOURNAMENT_DATA = {
        # 'test': test.TestTournament
    }
else:
    TOURNAMENT_DATA = {
        'alttprcd': alttprcd.ALTTPRCDTournament,
        # 'alttpr': alttpr.ALTTPRTournamentRace,
        # 'smwde': smwde.SMWDETournament,
        'alttprfr': alttprfr.ALTTPRFRTournament,
        # 'alttprhmg': alttprhmg.ALTTPRHMGTournament,
        'alttpres': alttpres.ALTTPRESTournament,
        'smz3coop': smz3coop.SMZ3CoopTournament,
        'smbingo': smbingo.SMBingoTournament,
        'alttprdaily': alttprdaily.AlttprSGDailyRace,
        'smz3': smz3.SMZ3DailyRace,
        # 'invleague': alttprleague.ALTTPRLeague,
        # 'alttprleague': alttprleague.ALTTPROpenLeague,
    }

async def fetch_tournament_handler(event, episodeid: int, rtgg_handler=None):
    return await TOURNAMENT_DATA[event].construct(episodeid, rtgg_handler)

async def create_tournament_race_room(event, episodeid):
    event_data = await TOURNAMENT_DATA[event].get_config()
    rtgg_bot = racetime_bots[event_data.data.racetime_category]
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
            try:
                wks = await wb.worksheet(sheet_name)
            except gspread.exceptions.WorksheetNotFound:
                wks = await wb.add_worksheet(sheet_name, 50, 10)

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
