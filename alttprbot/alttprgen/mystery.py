import os

import aiofiles
import yaml

import pyz3r
from alttprbot.database import audit
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.util.alttpr_discord import alttpr

from ..util.http import request_generic


class WeightsetNotFoundException(SahasrahBotException):
    pass

async def generate_test_game(weightset='weighted', festive=False):
    basename = os.path.basename(f'{weightset}.yaml')

    try:
        async with aiofiles.open(os.path.join("weights", basename)) as f:
            weights = yaml.safe_load(await f.read())
    except FileNotFoundError as err:
        raise WeightsetNotFoundException(
            f'Could not find weightset {weightset}.  See a list of available weights at <https://l.synack.live/weights>') from err

    if festive:
        settings, customizer = festive_generate_random_settings(
            weights=weights)
    else:
        settings, customizer = pyz3r.mystery.generate_random_settings(
            weights=weights)

    return settings

async def generate_random_game(weightset='weighted', tournament=True, spoilers="off", custom_weightset_url=None, festive=False):
    basename = os.path.basename(f'{weightset}.yaml')

    if not weightset == 'custom':
        try:
            async with aiofiles.open(os.path.join("weights", basename)) as f:
                weights = yaml.safe_load(await f.read())
        except FileNotFoundError as err:
            raise WeightsetNotFoundException(
                f'Could not find weightset {weightset}.  See a list of available weights at <https://l.synack.live/weights>') from err
    elif weightset == 'custom' and custom_weightset_url:
        weights = await request_generic(custom_weightset_url, method='get', returntype='yaml')

    if festive:
        settings, customizer = festive_generate_random_settings(
            weights=weights, spoilers=spoilers)
    else:
        settings, customizer = pyz3r.mystery.generate_random_settings(
            weights=weights, spoilers=spoilers)

    settings['tournament'] = tournament

    seed = await alttpr(settings=settings, customizer=customizer, festive=festive)

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
