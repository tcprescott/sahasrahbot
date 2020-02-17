import os
import random

import aiofiles
import pyz3r
import yaml

from alttprbot.database import audit, config
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.util.alttpr_discord import alttpr


class PresetNotFoundException(SahasrahBotException):
    pass


async def get_preset(preset, hints=False, nohints=False, spoilers="off", tournament=True, randomizer='alttpr'):
    # make sure someone isn't trying some path traversal shennaniganons
    basename = os.path.basename(f'{preset}.yaml')
    try:
        async with aiofiles.open(os.path.join(f"presets/{randomizer}", basename)) as f:
            preset_dict = yaml.safe_load(await f.read())
        if preset_dict.get('festive') and not await config.get(0, 'FestiveMode') == "true":
            raise PresetNotFoundException(
                f'Could not find preset {preset}.  See a list of available presets at <https://l.synack.live/presets>')
    except FileNotFoundError as err:
        raise PresetNotFoundException(
            f'Could not find preset {preset}.  See a list of available presets at <https://l.synack.live/presets>') from err

    if randomizer == 'alttpr':
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

        seed = await alttpr(
            customizer=preset_dict.get('customizer', False),
            festive=preset_dict.get('festive', False),
            settings=preset_dict['settings']
        )
        hash_id = seed.hash
    elif randomizer in ['sm', 'smz3']:
        if preset_dict.get('use_new', True):
            preset_dict['settings']['race'] = "true" if tournament else "false"
            seed = await pyz3r.sm(
                randomizer=randomizer,
                settings=preset_dict['settings']
            )
            hash_id = seed.slug_id
        else:
            if randomizer == 'sm':
                raise SahasrahBotException('Super Metroid randomizer is only supported on new version.')
            preset_dict['settings']['tournament'] = tournament
            seed = await pyz3r.smz3(
                settings=preset_dict['settings']
            )
            hash_id = seed.hash
    else:
        raise SahasrahBotException(f'Randomizer {randomizer} is not supported.')

    await audit.insert_generated_game(
        randomizer=randomizer,
        hash_id=hash_id,
        permalink=seed.url,
        settings=preset_dict['settings'],
        gentype='preset',
        genoption=preset
    )
    return seed, preset_dict
