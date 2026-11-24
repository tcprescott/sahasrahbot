"""The ALTTPR Ladder's public API (alttprladder.com), and the archive of the
pre-2.0 ladder (archive.alttprladder.com)."""
from datetime import datetime

import aiohttp

LADDER_API = 'https://alttprladder.com/api/v1/PublicAPI'
ARCHIVE_API = 'https://archive.alttprladder.com/api/v1/PublicAPI'
HEADERS = {'User-Agent': 'SahasrahBot'}


async def _get_json(url: str):
    async with aiohttp.request(method='get', url=url, headers=HEADERS, raise_for_status=True) as resp:
        return await resp.json()


async def get_active_racers() -> list:
    return await _get_json(f'{LADDER_API}/GetActiveRacers')


async def get_racer_guid(discord_username: str):
    """The ladder's GUID for the racer with this Discord name, or None."""
    for racer in await get_active_racers():
        if racer['DiscordName'] == discord_username:
            return racer['RacerGUID']
    return None


async def get_racer_history(racer_guid) -> list:
    """Per-flag race results for a racer: ``[{'Results': [{'StartDateTime': ...}, ...]}, ...]``."""
    return await _get_json(f'{LADDER_API}/GetRacerHistory?RacerGUID={racer_guid}&flag_id=0')


async def get_archive_race_count(discord_id, start: datetime, end: datetime) -> int:
    """How many races the old ladder recorded for this Discord user between two dates."""
    data = await _get_json(
        f"{ARCHIVE_API}/GetRacerRaceHistory?discordid={discord_id}"
        f"&startdt={start.strftime('%m%d%Y')}&enddt={end.strftime('%m%d%Y')}"
    )
    return data['TotalCount']

