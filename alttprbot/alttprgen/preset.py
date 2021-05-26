import os
import random

import aiofiles
import yaml

import pyz3r
from alttprbot import models
from alttprbot.database import config
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.util.alttpr_discord import alttpr
from alttprbot_discord.util.alttprdoors_discord import AlttprDoorDiscord

SMZ3_ENVIRONMENTS = {
    'live': {
        'smz3': 'https://samus.link',
        'sm': 'https://sm.samus.link',
    },
    'beta': {
        'smz3': 'https://beta.samus.link',
        'sm': 'https://sm.beta.samus.link',
    },
    'alpha': {
        'smz3': 'https://alpha.samus.link',
        'sm': 'https://sm.beta.samus.link',
    }
}


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
                f'Could not find preset {preset}.  See a list of available presets at https://sahasrahbot.synack.live/presets.html')
    except FileNotFoundError as err:
        raise PresetNotFoundException(
            f'Could not find preset {preset}.  See a list of available presets at https://sahasrahbot.synack.live/presets.html') from err

    return preset_dict


async def generate_preset(preset_dict, preset=None, hints=False, nohints=False, spoilers="off", tournament=True, allow_quickswap=False):
    randomizer = preset_dict.get('randomizer', 'alttpr')
    settings = preset_dict['settings']

    if randomizer == 'alttpr':
        if preset_dict.get('doors', False):
            if hints:
                settings['hints'] = 'on'
            elif nohints:
                settings['hints'] = 'off'

            if allow_quickswap:
                settings['quickswap'] = True

            seed = await AlttprDoorDiscord.create(
                settings=settings,
                spoilers=spoilers == "on"
            )
            hash_id = seed.hash
        else:
            if hints:
                settings['hints'] = 'on'
            elif nohints:
                settings['hints'] = 'off'

            settings['tournament'] = tournament
            settings['spoilers'] = spoilers

            if not 'allow_quickswap' in settings:
                settings['allow_quickswap'] = allow_quickswap

            if preset_dict.get('customizer', False):
                if 'l' not in settings:
                    settings['l'] = {}
                for i in preset_dict.get('forced_locations', {}):
                    location = random.choice([l for l in i['locations'] if l not in settings['l']])
                    settings['l'][location] = i['item']

            seed = await alttpr(
                customizer=preset_dict.get('customizer', False),
                festive=preset_dict.get('festive', False),
                settings=settings
            )
            hash_id = seed.hash

    # elif randomizer == 'alttprdoors':

    elif randomizer in ['sm', 'smz3']:
        settings['race'] = "true" if tournament else "false"
        seed = await pyz3r.sm(
            randomizer=randomizer,
            settings=settings,
            baseurl=SMZ3_ENVIRONMENTS[preset_dict.get('env', 'live')][randomizer],
        )
        hash_id = seed.slug_id

    else:
        raise SahasrahBotException(
            f'Randomizer {randomizer} is not supported.')

    await models.AuditGeneratedGames.create(
        randomizer=randomizer,
        hash_id=hash_id,
        permalink=seed.url,
        settings=settings,
        gentype='preset',
        genoption=preset,
        customizer=1 if preset_dict.get('customizer', False) else 0
    )
    return seed
