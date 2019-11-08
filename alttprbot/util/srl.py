from config import Config as c
import aiofiles
import json
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

async def send_irc_message(raceid, message):
    if c.DEBUG: return
    data = {
        'auth': c.InternalApiToken,
        'channel': f'#srl-{raceid}',
        'message': message
    }
    await http.request_json_post('http://localhost:5000/api/message', data=data, auth=None, returntype='text')