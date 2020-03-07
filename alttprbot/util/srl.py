import json
import re

import aiofiles

from config import Config as c

from . import http


async def get_race(raceid, complete=False):
    # if we're developing locally, we want to have some artifical data to use that isn't from SRL
    if c.DEBUG:
        if raceid == "test":
            async with aiofiles.open('test_input/srl_test.json', 'r') as f:
                return json.loads(await f.read(), strict=False)
        elif raceid == "test2" and not complete:
            async with aiofiles.open('test_input/srl_open.json', 'r') as f:
                return json.loads(await f.read(), strict=False)
        elif raceid == "test2" and complete:
            async with aiofiles.open('test_input/srl_complete.json', 'r') as f:
                return json.loads(await f.read(), strict=False)
        elif raceid == 'rip':
            return {}

    return await http.request_generic(f'http://api.speedrunslive.com/races/{raceid}', returntype='json')

def srl_race_id(channel):
    if channel == '#srl-synack-testing':
        return 'test'
    if re.search('^#srl-[a-z0-9]{5}$', channel):
        return channel.partition('-')[-1]

async def get_all_races():
    return await http.request_generic(f'http://api.speedrunslive.com/races', returntype='json')

async def get_player(player):
    return await http.request_generic(f'http://api.speedrunslive.com/players/{player}', returntype='json')

async def get_pastraces(game, player, pagesize=20):
    # if we're developing locally, we want to have some artifical data to use that isn't from SRL
    if c.DEBUG:
        if player == "test0":
            async with aiofiles.open('test_input/srl_pastraces.json', 'r') as f:
                return json.loads(await f.read(), strict=False)
        elif player == "test1":
            async with aiofiles.open('test_input/srl_pastraces_empty.json', 'r') as f:
                return json.loads(await f.read(), strict=False)

    params = {
        'game': game,
        'player': player,
        'pageSize': pagesize
    }
    return await http.request_generic('http://api.speedrunslive.com/pastraces', returntype='json', reqparams=params)
