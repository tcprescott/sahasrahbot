"""Recording finished tournament races to each event's Google Sheet.

Run by the ``record_races`` scheduled job (``alttprbot/services/tournament_jobs.py``).
Events with ``auto_record`` on also get the race recorded on racetime.gg.
"""
import datetime
import logging

import gspread.exceptions
import gspread_asyncio
import isodate
import pytz

import config
from alttprbot import models, tournaments
from alttprbot.integrations import racetime
from alttprbot.util import gsheet

logger = logging.getLogger(__name__)

SHEET_HEADER = [
    'episode',
    'start time (eastern)',
    'racetime',
    'winner',
    'loser',
    'winner finish',
    'loser finish',
    'permalink',
    'spoiler',
]


async def record_results():
    agcm = gspread_asyncio.AsyncioGspreadClientManager(gsheet.get_creds)
    agc = await agcm.authorize()

    for event, event_obj in tournaments.TOURNAMENT_DATA.items():
        event_data = await event_obj.get_config()
        if event_data.data.gsheet_id is None:
            continue

        wb = await agc.open_by_key(event_data.data.gsheet_id)

        races = await models.TournamentResults.filter(written_to_gsheet=None, event=event)

        if not races:
            continue

        wks = await _worksheet(wb, event)

        for race in races:
            logger.info(f"Recording {race.episode_id} for {event} to {event_data.data.gsheet_id}")
            try:
                await _record_race(wks, race, event_data.data)
            except Exception:
                logger.exception("Encountered a problem when attempting to record a race.")

    logger.debug('done')


async def _worksheet(wb, event: str):
    """The event's tab in its workbook, created with a header row if missing."""
    try:
        return await wb.worksheet(event)
    except gspread.exceptions.WorksheetNotFound:
        wks = await wb.add_worksheet(event, 50, 10)
        await wks.append_row(values=SHEET_HEADER)
        return wks


async def _record_race(wks, race: models.TournamentResults, settings) -> None:
    """Write one finished race once its stream delay is over; forget a cancelled one."""
    race_data = await racetime.get_race(race.srl_id)
    status = race_data['status']['value']

    if status == 'cancelled':
        await race.delete()
        return
    if status != 'finished':
        return

    row = result_row(race, race_data, stream_delay=settings.stream_delay)
    if row is None:
        return

    await wks.append_row(values=row)
    race.status = "RECORDED"
    race.written_to_gsheet = 1
    await race.save()

    if settings.auto_record:
        await racetime.record_race(race_data)


def result_row(race: models.TournamentResults, race_data: dict, stream_delay: int, now: datetime.datetime = None):
    """The sheet row for a finished race, or None while it's still inside the stream delay."""
    winner = [e for e in race_data['entrants'] if e['place'] == 1][0]
    runnerup = [e for e in race_data['entrants'] if e['place'] in [2, None]][0]

    started_at = isodate.parse_datetime(race_data['started_at']).astimezone(pytz.timezone('US/Eastern'))
    ended_at = isodate.parse_datetime(race_data['ended_at'])
    record_at = ended_at + datetime.timedelta(minutes=stream_delay)

    if record_at > (now or datetime.datetime.now(tz=datetime.timezone.utc)):
        return None

    return [
        race.episode_id,
        started_at.strftime("%Y-%m-%d %H:%M:%S"),
        f"{config.RACETIME_URL}/{race.srl_id}",
        winner['user']['name'],
        runnerup['user']['name'],
        finish_time(winner),
        finish_time(runnerup),
        race.permalink,
        race.spoiler
    ]


def finish_time(entrant: dict):
    return str(isodate.parse_duration(entrant['finish_time'])) if isinstance(entrant['finish_time'], str) else None
