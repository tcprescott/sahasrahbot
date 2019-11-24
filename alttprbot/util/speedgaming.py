from . import http
from config import Config as c
import aiofiles
import json

async def get_episode(episodeid, complete=False):
    # if we're developing locally, we want to have some artifical data to use that isn't from SpeedGaming
    if c.DEBUG:
        if episodeid == 1:
            async with aiofiles.open('test_input/sg_1.json', 'r') as f:
                return json.loads(await f.read(), strict=False)
        elif episodeid == 2 and not complete:
            async with aiofiles.open('test_input/sg_2.json', 'r') as f:
                return json.loads(await f.read(), strict=False)
        elif episodeid == 3 and complete:
            async with aiofiles.open('test_input/sg_3.json', 'r') as f:
                return json.loads(await f.read(), strict=False)
        elif episodeid == 0:
            return {"error":"Failed to find episode with id 0."}

    return await http.request_generic(f'{c.SgApiEndpoint}/episode', reqparams={'id': episodeid}, returntype='json')