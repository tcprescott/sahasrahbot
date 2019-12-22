import os
import random

import aiofiles
import yaml

from config import Config as c

from ..util.alttpr_discord import alttpr


class PresetNotFoundException(Exception):
    pass


async def get_preset(preset, hints=False, nohints=False, spoilers="off", tournament=True):
    # make sure someone isn't trying some path traversal shennaniganons
    basename = os.path.basename(f'{preset}.yaml')
    try:
        async with aiofiles.open(os.path.join("presets", basename)) as f:
            preset_dict = yaml.load(await f.read(), Loader=yaml.FullLoader)
        if preset_dict.get('festive') and not c.FESTIVEMODE:
            raise PresetNotFoundException(
                f'Could not find preset {preset}.  See a list of available presets at <https://l.synack.live/presets>')
    except FileNotFoundError:
        raise PresetNotFoundException(
            f'Could not find preset {preset}.  See a list of available presets at <https://l.synack.live/presets>')

    if hints:
        preset_dict['settings']['hints'] = 'on'
    elif nohints:
        preset_dict['settings']['hints'] = 'off'

    preset_dict['settings']['tournament'] = tournament
    preset_dict['settings']['spoilers'] = spoilers

    if preset_dict.get('shuffle_prize_packs', False) and preset_dict.get('customizer', False):
        p = ['0', '1', '2', '3', '4', '5', '6']
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

    seed = await alttpr(customizer=preset_dict.get('customizer', False), festive=preset_dict.get('festive', False), settings=preset_dict['settings'])
    return seed, preset_dict
