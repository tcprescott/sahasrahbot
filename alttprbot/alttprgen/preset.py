import os
import random
import json

import aiofiles
from ..util.alttpr_discord import alttpr
import yaml

from config import Config as c

class PresetNotFoundException(Exception):
    pass

async def get_preset(preset, hints=False, nohints=False, spoilers="off"):
    # make sure someone isn't trying some path traversal shennaniganons
    basename = os.path.basename(f'{preset}.yaml')
    try:
        async with aiofiles.open(os.path.join("presets", basename)) as f:
            preset_dict = yaml.load(await f.read(), Loader=yaml.FullLoader)
    except FileNotFoundError:
        raise PresetNotFoundException(f'Could not find preset {preset}')

    if hints:
        preset_dict['settings']['hints'] = 'on'
    elif nohints:
        preset_dict['settings']['hints'] = 'off'

    preset_dict['settings']['tournament'] = True
    preset_dict['settings']['spoilers'] = spoilers

    if 'shuffle_prize_packs' in preset_dict and preset_dict['shuffle_prize_packs'] and preset_dict['customizer']:
        p = ['0','1','2','3','4','5','6']
        random.shuffle(p)
        # print(p)

        packs = {}
        packs[p[0]] = preset_dict['settings']['drops']['0']
        packs[p[1]] = preset_dict['settings']['drops']['1']
        packs[p[2]] = preset_dict['settings']['drops']['2']
        packs[p[3]] = preset_dict['settings']['drops']['3']
        packs[p[4]] = preset_dict['settings']['drops']['4']
        packs[p[5]] = preset_dict['settings']['drops']['5']
        packs[p[6]] = preset_dict['settings']['drops']['6']
        packs['crab'] = preset_dict['settings']['drops']['crab']
        packs['fish'] = preset_dict['settings']['drops']['fish']
        packs['pull'] = preset_dict['settings']['drops']['pull']
        packs['stun'] = preset_dict['settings']['drops']['stun']

        preset_dict['settings']['drops'] = packs

    # print(json.dumps(preset_dict['settings'], indent=4))

    seed = await alttpr(customizer=preset_dict['customizer'], settings=preset_dict['settings'])
    return seed, preset_dict
