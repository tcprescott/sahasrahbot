import json
import random
import string
from collections import OrderedDict

import aiofiles
import pyz3r

from config import Config as c

from .preset import get_preset


async def generate_spoiler_game(preset):
    seed, preset_dict = await get_preset(preset, hints=False, spoilers="generate")
    if not seed:
        return False, False, False
    spoiler_log_url = await write_json_to_disk(seed)
    return seed, preset_dict, spoiler_log_url

async def write_json_to_disk(seed):
    code = await seed.code()
    filename = f"spoiler__{seed.hash}__{'-'.join(code).replace(' ', '')}__{''.join(random.choices(string.ascii_letters + string.digits, k=4))}.txt"

    sorteddict = seed.get_formatted_spoiler()

    async with aiofiles.open(f"{c.SpoilerLogLocal}/{filename}", "w+", newline='\r\n') as out:
        await out.write(json.dumps(sorteddict, indent=4))
        await out.flush()

    # async with aiofiles.open(f"{c.SpoilerLogLocal}/{filename}", "w+", newline='\r\n') as out:
    #     dump = yaml.dump(sorteddict)
    #     await out.write(dump)

    return c.SpoilerLogUrlBase + '/' + filename