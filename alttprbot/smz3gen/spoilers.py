import json
import random
import string
from collections import OrderedDict

import aiofiles
import pyz3r.misc

from config import Config as c

from .preset import get_preset


async def generate_spoiler_game(preset):
    seed = await get_preset(preset)
    if not seed:
        return False, False
    spoiler_log_url = await write_json_to_disk(seed)
    return seed, spoiler_log_url

async def write_json_to_disk(seed):
    filename = f"smz3_spoiler__{seed.hash}__{''.join(random.choices(string.ascii_letters + string.digits, k=4))}.txt"

    # magic happens here to make it pretty-printed and tournament-compliant
    s = seed.data['spoiler']

    sorteddict = OrderedDict() 

    sectionlist = [
        'Special',
        'Hyrule Castle',
        'Eastern Palace',
        'Desert Palace',
        'Tower Of Hera',
        'Dark Palace',
        'Swamp Palace',
        'Skull Woods',
        'Thieves Town',
        'Ice Palace',
        'Misery Mire',
        'Turtle Rock',
        'Ganons Tower',
        'Light World',
        'Death Mountain',
        'Dark World',
        'Crateria',
        'Brinstar',
        'Norfair',
        'Lower Norfair',
        'Wrecked Ship',
        'Maridia'
    ]
    prizemap = [
        ['Eastern Palace', 'Eastern Palace - Prize'],
        ['Desert Palace', 'Desert Palace - Prize'],
        ['Tower Of Hera', 'Tower of Hera - Prize'],
        ['Dark Palace', 'Palace of Darkness - Prize'],
        ['Swamp Palace', 'Swamp Palace - Prize'],
        ['Skull Woods', 'Skull Woods - Prize'],
        ['Thieves Town', 'Thieves\' Town - Prize'],
        ['Ice Palace', 'Ice Palace - Prize'],
        ['Misery Mire', 'Misery Mire - Prize'],
        ['Turtle Rock', 'Turtle Rock - Prize'],
    ]

    sorteddict['Prizes'] = {}
    for dungeon, prize in prizemap:
        sorteddict['Prizes'][dungeon] = s[dungeon][prize]

    for section in sectionlist:
        sorteddict[section] = s[section]

    sorteddict['meta']           = s['meta']
    sorteddict['meta']['hash']   = seed.hash
    sorteddict['meta']['permalink'] = seed.url

    for dungeon, prize in prizemap:
        del sorteddict[dungeon][prize]

    async with aiofiles.open(f"{c.SpoilerLogLocal}/{filename}", "w+", newline='\r\n') as out:
        await out.write(json.dumps(sorteddict, indent=4))
        await out.flush()

    # async with aiofiles.open(f"{c.SpoilerLogLocal}/{filename}", "w+", newline='\r\n') as out:
    #     dump = yaml.dump(sorteddict)
    #     await out.write(dump)

    return c.SpoilerLogUrlBase + '/' + filename

