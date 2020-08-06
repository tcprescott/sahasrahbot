import os

import aiofiles
import pyz3r
import yaml

from alttprbot.database import audit, config
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.util.alttpr_discord import alttpr


class PresetNotFoundException(SahasrahBotException):
    pass

# this is until I port the existing code over to the new fetch_preset and generate_preset coroutines, or do something else that isn't as terrible
async def get_preset(preset, hints=False, nohints=False, spoilers="off", tournament=True, randomizer='alttpr', allow_quickswap=False):
    preset_dict = await fetch_preset(preset, randomizer)
    seed = await generate_preset(preset_dict, preset=preset, hints=hints, nohints=nohints, spoilers=spoilers, tournament=tournament, allow_quickswap=allow_quickswap)
    return seed, preset_dict

async def fetch_preset(preset, randomizer='alttpr'):
    preset = preset.lower()

    # make sure someone isn't trying some path traversal shennaniganons
    basename = os.path.basename(f'{preset}.yaml')

    try:
        async with aiofiles.open(os.path.join(f"presets/{randomizer}", basename)) as f:
            preset_dict = yaml.safe_load(await f.read())
        if preset_dict.get('festive') and not await config.get(0, 'FestiveMode') == "true":
            raise PresetNotFoundException(
                f'Could not find preset {preset}.  See a list of available presets at https://l.synack.live/presets')
    except FileNotFoundError as err:
        raise PresetNotFoundException(
            f'Could not find preset {preset}.  See a list of available presets at https://l.synack.live/presets') from err

    return preset_dict

async def generate_preset(preset_dict, preset=None, hints=False, nohints=False, spoilers="off", tournament=True, allow_quickswap=False):
    randomizer = preset_dict.get('randomizer', 'alttpr')

    if randomizer == 'alttpr':
        if hints:
            preset_dict['settings']['hints'] = 'on'
        elif nohints:
            preset_dict['settings']['hints'] = 'off'

        preset_dict['settings']['tournament'] = tournament
        preset_dict['settings']['spoilers'] = spoilers

        if allow_quickswap:
            preset_dict['settings']['allow_quickswap'] = True

        seed = await alttpr(
            customizer=preset_dict.get('customizer', False),
            festive=preset_dict.get('festive', False),
            settings=preset_dict['settings']
        )
        hash_id = seed.hash
    elif randomizer in ['sm', 'smz3']:
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
    return seed
