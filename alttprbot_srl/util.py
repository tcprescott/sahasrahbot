import re
from alttprbot.util.http import request_generic, request_json_post

def srl_race_id(channel):
    if re.search('^#srl-[a-z0-9]{5}$', channel):
        return channel.partition('-')[-1]

async def get_race(raceid):
    return await request_generic(f'http://api.speedrunslive.com/races/{raceid}', returntype='json')

async def get_all_races():
    return await request_generic(f'http://api.speedrunslive.com/races', returntype='json')