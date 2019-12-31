import os
import random

import aiofiles
import pyz3r
import yaml

from alttprbot_discord.util.alttpr_discord import alttpr
from ..util.http import request_generic


class WeightsetNotFoundException(Exception):
    pass


async def generate_random_game(weightset='weighted', tournament=True, spoilers="off", custom_weightset_url=None, festive=False):
    basename = os.path.basename(f'{weightset}.yaml')

    if not weightset == 'custom':
        try:
            async with aiofiles.open(os.path.join("weights", basename)) as f:
                weights = yaml.safe_load(await f.read())
        except FileNotFoundError:
            raise WeightsetNotFoundException(
                f'Could not find weightset {weightset}.  See a list of available weights at <https://l.synack.live/weights>')
    elif weightset == 'custom' and custom_weightset_url:
        weights = await request_generic(custom_weightset_url, method='get', returntype='yaml')

    if festive:
        settings = festive_generate_random_settings(
            weights=weights, spoilers=spoilers)
    else:
        settings = pyz3r.mystery.generate_random_settings(
            weights=weights, spoilers=spoilers)

    settings['tournament'] = tournament

    # Stop gap measure until swordless entrance with a hard+ item pool is fixed
    if settings.get('entrances', 'none') != 'none' and settings['item']['pool'] in ['hard', 'expert'] and settings['weapons'] == 'swordless':
        settings['weapons'] = 'randomized'

    seed = await alttpr(settings=settings, festive=festive)
    return seed


def festive_generate_random_settings(weights, tournament=True, spoilers="mystery"):
    settings = {
        "glitches": get_random_option(weights['glitches_required']),
        "item_placement": get_random_option(weights['item_placement']),
        "dungeon_items": get_random_option(weights['dungeon_items']),
        "accessibility": get_random_option(weights['accessibility']),
        "hints": get_random_option(weights['hints']),
        "weapons": get_random_option(weights['weapons']),
        "item": {
            "pool": get_random_option(weights['item_pool']),
            "functionality": get_random_option(weights['item_functionality']),
        },
        "tournament": tournament,
        "spoilers": spoilers,
        "lang": "en"
    }

    return settings


def get_random_option(optset):
    return random.choices(population=list(optset.keys()), weights=list(optset.values()))[0]
