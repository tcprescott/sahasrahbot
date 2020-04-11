import os

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

    if preset_dict.get('randomizer', randomizer) == 'alttpr':
        if hints:
            preset_dict['settings']['hints'] = 'on'
        elif nohints:
            preset_dict['settings']['hints'] = 'off'

        preset_dict['settings']['tournament'] = tournament
        preset_dict['settings']['spoilers'] = spoilers

        seed = await alttpr(
            customizer=preset_dict.get('customizer', False),
            festive=preset_dict.get('festive', False),
            settings=preset_dict['settings']
        )
        hash_id = seed.hash
    elif preset_dict.get('randomizer', randomizer) in ['sm', 'smz3']:
        preset_dict['settings']['race'] = "true" if tournament else "false"
        seed = await pyz3r.sm(
            randomizer=randomizer,
            settings=preset_dict['settings']
        )
        hash_id = seed.slug_id
    else:
        raise SahasrahBotException(f'Randomizer {randomizer} is not supported.')

    await audit.insert_generated_game(
        randomizer=randomizer,
        hash_id=hash_id,
        permalink=seed.url,
        settings=preset_dict['settings'],
        gentype='preset',
        genoption=preset,
        customizer=1 if preset_dict.get('customizer', False) else 0
    )
    return seed, preset_dict
