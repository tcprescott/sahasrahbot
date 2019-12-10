import random
from ..util.alttpr_discord import alttpr
from ..util.http import request_generic
import os
import aiofiles
import yaml
from config import Config as c

class WeightsetNotFoundException(Exception):
    pass

async def generate_random_game(weightset='weighted', tournament=True, spoilers="off", custom_weightset_url=None):
    basename = os.path.basename(f'{weightset}.yaml')

    if not weightset == 'custom':
        try:
            async with aiofiles.open(os.path.join("weights", basename)) as f:
                o = yaml.load(await f.read(), Loader=yaml.FullLoader)
        except FileNotFoundError:
            raise WeightsetNotFoundException(f'Could not find weightset {weightset}.  See a list of available weights at <https://l.synack.live/weights>')
    elif weightset == 'custom' and custom_weightset_url:
        o = await request_generic(custom_weightset_url, method='get', returntype='yaml')


    settings={
        "glitches": get_random_option(o['glitches_required']),
        "item_placement": get_random_option(o['item_placement']),
        "dungeon_items": get_random_option(o['dungeon_items']),
        "accessibility": get_random_option(o['accessibility']),
        "goal": get_random_option(o['goals']),
        "crystals": {
            "ganon": get_random_option(o['tower_open']),
            "tower": get_random_option(o['ganon_open']),
        },
        "mode": get_random_option(o['world_state']),
        "entrances": get_random_option(o['entrance_shuffle']),
        "hints": get_random_option(o['hints']),
        "weapons": get_random_option(o['weapons']),
        "item": {
            "pool": get_random_option(o['item_pool']),
            "functionality": get_random_option(o['item_functionality']),
        },
        "tournament": tournament,
        "spoilers": spoilers,
        "lang": "en",
        "enemizer": {
            "boss_shuffle": get_random_option(o['boss_shuffle']),
            "enemy_shuffle": get_random_option(o['enemy_shuffle']),
            "enemy_damage": get_random_option(o['enemy_damage']),
            "enemy_health": get_random_option(o['enemy_health']),
        }
    }

    # This if statement is dedicated to the survivors of http://www.speedrunslive.com/races/result/#!/264658
    if settings['weapons'] not in ['vanilla','assured'] and settings['mode'] == 'standard' and (
            settings['enemizer']['enemy_shuffle'] != 'none'
            or settings['enemizer']['enemy_damage'] != 'default'
            or settings['enemizer']['enemy_health'] != 'default'):
        settings['weapons'] = 'assured'

    seed = await alttpr(settings=settings)
    return seed

def get_random_option(optset):
    return random.choices(population=list(optset.keys()),weights=list(optset.values()))[0]