import os

import aiofiles
import yaml
from aiohttp.client_exceptions import ClientResponseError
from tenacity import RetryError, AsyncRetrying, stop_after_attempt, retry_if_exception_type

import pyz3r
from alttprbot.alttprgen.preset import fetch_preset
from alttprbot.database import audit
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.util.alttpr_discord import alttpr


class WeightsetNotFoundException(SahasrahBotException):
    pass


async def generate_test_game(weightset='weighted', festive=False):
    weights = await get_weights(weightset)

    if festive:
        settings, _ = festive_generate_random_settings(
            weights=weights)
    else:
        settings, _ = pyz3r.mystery.generate_random_settings(
            weights=weights)

    return settings


async def get_weights(weightset='weighted'):
    basename = os.path.basename(f'{weightset}.yaml')

    try:
        async with aiofiles.open(os.path.join("weights", basename)) as f:
            weights = yaml.safe_load(await f.read())
    except FileNotFoundError as err:
        raise WeightsetNotFoundException(
            f'Could not find weightset {weightset}.  See a list of available weights at https://sahasrahbot.synack.live/mystery.html') from err

    return weights


async def generate_random_game(weightset='weighted', weights=None, tournament=True, spoilers="off", festive=False):
    if weights is None:
        weights = await get_weights(weightset)

    try:
        async for attempt in AsyncRetrying(stop=stop_after_attempt(5), retry=retry_if_exception_type(ClientResponseError)):
            with attempt:
                try:
                    settings, customizer = await generate_random_settings(weights, festive=festive, spoilers=spoilers)

                    settings['tournament'] = tournament
                    seed = await alttpr(settings=settings, customizer=customizer, festive=festive)
                except ClientResponseError:
                    await audit.insert_generated_game(
                        randomizer='alttpr',
                        hash_id=None,
                        permalink=None,
                        settings=settings,
                        gentype='mystery failure',
                        genoption=weightset,
                        customizer=1 if customizer else 0
                    )
                    raise
    except RetryError as e:
        raise e.last_attempt._exception from e

    await audit.insert_generated_game(
        randomizer='alttpr',
        hash_id=seed.hash,
        permalink=seed.url,
        settings=settings,
        gentype='mystery',
        genoption=weightset,
        customizer=1 if customizer else 0
    )
    return seed


def festive_generate_random_settings(weights, tournament=True, spoilers="mystery"):
    settings = {
        "glitches": pyz3r.mystery.get_random_option(weights['glitches_required']),
        "item_placement": pyz3r.mystery.get_random_option(weights['item_placement']),
        "dungeon_items": pyz3r.mystery.get_random_option(weights['dungeon_items']),
        "accessibility": pyz3r.mystery.get_random_option(weights['accessibility']),
        "hints": pyz3r.mystery.get_random_option(weights['hints']),
        "weapons": pyz3r.mystery.get_random_option(weights['weapons']),
        "item": {
            "pool": pyz3r.mystery.get_random_option(weights['item_pool']),
            "functionality": pyz3r.mystery.get_random_option(weights['item_functionality']),
        },
        "tournament": tournament,
        "spoilers": spoilers,
        "lang": "en"
    }

    return settings, False


async def generate_random_settings(weights, festive=False, spoilers="mystery"):
    if festive:
        settings, customizer = festive_generate_random_settings(
            weights=weights, spoilers=spoilers)
    else:
        if 'preset' in weights:
            rolledpreset = pyz3r.mystery.get_random_option(weights['preset'])
            if rolledpreset == 'none':
                settings, customizer = pyz3r.mystery.generate_random_settings(
                    weights=weights, spoilers=spoilers)
            else:
                preset_dict = await fetch_preset(rolledpreset, randomizer='alttpr')
                settings = preset_dict['settings']
                customizer = preset_dict.get('customizer', False)
                settings.pop('name', None)
                settings.pop('notes', None)
                settings['spoilers'] = spoilers
        else:
            settings, customizer = pyz3r.mystery.generate_random_settings(
                weights=weights, spoilers=spoilers)

    return settings, customizer
