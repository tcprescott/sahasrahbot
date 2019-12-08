from . import http
from config import Config as c
import aiofiles
import json

class SGEpisodeNotFoundException(Exception):
    pass

async def get_episode(episodeid, complete=False):
    # if we're developing locally, we want to have some artifical data to use that isn't from SpeedGaming
    if c.DEBUG:
        if episodeid == 1:
            async with aiofiles.open('test_input/sg_1.json', 'r') as f:
                result = json.loads(await f.read(), strict=False)
        elif episodeid == 2 and not complete:
            async with aiofiles.open('test_input/sg_2.json', 'r') as f:
                result = json.loads(await f.read(), strict=False)
        elif episodeid == 3 and complete:
            async with aiofiles.open('test_input/sg_3.json', 'r') as f:
                result = json.loads(await f.read(), strict=False)
        elif episodeid == 0:
           result = {"error":"Failed to find episode with id 0."}
        else:
            result = await http.request_generic(f'{c.SgApiEndpoint}/episode', reqparams={'id': episodeid}, returntype='json')
    else:
        result = await http.request_generic(f'{c.SgApiEndpoint}/episode', reqparams={'id': episodeid}, returntype='json')

    if 'error' in result:
        raise SGEpisodeNotFoundException(result["error"])

    if not result['event']['slug'] == 'alttpr':
        raise SGEpisodeNotFoundException('Not an alttpr tournament race.')

    return result