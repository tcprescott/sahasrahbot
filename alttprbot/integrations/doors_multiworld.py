"""The ALTTP Door Randomizer multiworld server's HTTP API.

It runs next to the bot, on localhost:5002. Every call returns the server's JSON
reply as-is; the server reports failures in the body (``success: False`` with
an ``error`` or ``description``), and callers decide what to do with them. A reply that
isn't JSON raises ``MultiworldServerError``.
"""
import aiohttp

BASE_URL = 'http://localhost:5002'


class MultiworldServerError(Exception):
    """The server's reply wasn't usable JSON (``aiohttp.ClientResponseError``, chained)."""


async def _request(method: str, path: str, **kwargs):
    try:
        async with aiohttp.ClientSession() as session, session.request(method, f'{BASE_URL}{path}', **kwargs) as resp:
            return await resp.json()
    except aiohttp.ClientResponseError as err:
        raise MultiworldServerError(str(err)) from err


async def create_game(data: dict) -> dict:
    """Host a new game (``multidata_url`` …) or resume a closed one (``token``)."""
    return await _request('post', '/game', json=data)


async def get_game(token: str) -> dict:
    return await _request('get', f'/game/{token}')


async def send_command(token: str, data: dict) -> dict:
    return await _request('put', f'/game/{token}/cmd', json=data)


async def send_message(token: str, msg: str) -> dict:
    return await _request('put', f'/game/{token}/msg', json={'msg': msg})


async def autocomplete_players(token: str, current: str) -> list:
    return await _request('get', '/autocomplete/players', params={'player': current, 'token': token})


async def autocomplete_items(current: str) -> list:
    return await _request('get', '/autocomplete/items', params={'item': current})


async def autocomplete_clients(token: str, current: str) -> list:
    return await _request('get', '/autocomplete/clients', params={'client': current, 'token': token})
