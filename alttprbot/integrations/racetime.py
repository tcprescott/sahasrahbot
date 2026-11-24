"""racetime.gg's public JSON API, and the race-recording form only a logged-in
category moderator can submit.

``base_url`` defaults to ``config.RACETIME_URL``; callers that talk to a
specific bot's host pass that bot's base URL.
"""
import json
import logging

import aiohttp
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)


class RacetimeRecordError(Exception):
    """The race page needed to record a race couldn't be fetched or had no CSRF token."""


def _base(base_url):
    return config.RACETIME_URL if base_url is None else base_url


async def get_race(room_name: str, base_url: str = None) -> dict:
    """``/<category>/<room>/data``. Raises ``aiohttp.ClientResponseError`` on an HTTP error."""
    async with aiohttp.request(method='get', url=f"{_base(base_url)}/{room_name}/data",
                               raise_for_status=True) as resp:
        return json.loads(await resp.read())


async def get_user(racetime_id: str, base_url: str = None) -> dict:
    """``/user/<id>/data``. Raises ``aiohttp.ClientResponseError`` on an HTTP error."""
    async with aiohttp.request(method='get', url=f"{_base(base_url)}/user/{racetime_id}/data",
                               raise_for_status=True) as resp:
        return json.loads(await resp.read())


async def get_user_races_page(racetime_id: str, page: int, base_url: str = None):
    """One page of ``/user/<id>/races/data``, or None when the reply isn't JSON
    (racetime.gg answers an unknown user with an HTML page)."""
    async with aiohttp.request(
            method='get',
            url=f"{_base(base_url)}/user/{racetime_id}/races/data",
            params={'page': page}
    ) as resp:
        try:
            return await resp.json()
        except aiohttp.ContentTypeError:
            return None


async def record_race(race_data: dict, base_url: str = None) -> None:
    """Press "record" on a finished race, as the account in
    ``config.RACETIME_SESSION_TOKEN``/``RACETIME_CSRF_TOKEN``.

    Does nothing when the race is already recorded or can't be. racetime.gg has
    no API for this, so it scrapes the CSRF token from the race page and posts
    the monitor form. Raises ``RacetimeRecordError`` when the race page can't be
    fetched or has no token; a failed post is only logged.
    """
    base = _base(base_url)
    url = base + race_data['url']
    record_url = url + "/monitor/record"
    recorded = race_data.get('recorded', True)
    recordable = race_data.get('recordable', False)

    if recorded or not recordable:
        return

    cookies = {'sessionid': config.RACETIME_SESSION_TOKEN,
               'csrftoken': config.RACETIME_CSRF_TOKEN}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(
                    method='get',
                    url=url,
                    cookies=cookies,
                    raise_for_status=True
            ) as resp:
                soup = BeautifulSoup(await resp.text(), features="html5lib")
        except Exception as e:
            raise RacetimeRecordError("Unable to acquire CSRF token.  Please contact Synack for help.") from e

        token_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if token_input is None or not token_input.get('value'):
            raise RacetimeRecordError("Unable to acquire CSRF token.  Please contact Synack for help.")
        data = {'csrfmiddlewaretoken': token_input['value']}

        try:
            async with aiohttp.request(
                    method='post',
                    url=record_url,
                    cookies=cookies,
                    headers={'Origin': base,
                             'Referer': url},
                    data=data,
                    raise_for_status=True
            ):
                logger.info("Recorded %s on racetime.gg", race_data['url'])
        except Exception:
            logger.exception("Unable to automatically record race. Skipping...")
