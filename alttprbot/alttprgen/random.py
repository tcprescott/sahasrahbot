from .weights import weights
import random
import pyz3r
from config import Config as c

async def generate_random_game(logic='NoGlitches', weightset='weighted', tournament=True):
    try:
        if weightset == 'casual':
            o = weights['friendly']
        else:
            o = weights[weightset]
    except KeyError:
        raise Exception('Invalid weightset chosen.')

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
        "spoilers": False,
        "lang": "en",
        "enemizer": {
            "boss_shuffle": get_random_option(o['boss_shuffle']),
            "enemy_shuffle": get_random_option(o['enemy_shuffle']),
            "enemy_damage": get_random_option(o['enemy_damage']),
            "enemy_health": get_random_option(o['enemy_health']),
        }
    }

    # print(json.dumps(settings, indent=4))
    seed = await pyz3r.alttpr(
        baseurl=c.baseurl,
        seed_baseurl=c.seed_baseurl,
        username=c.username,
        password=c.password,
        settings=settings
    )
    return seed

def get_random_option(optset):
    return random.choices(population=list(optset.keys()),weights=list(optset.values()))[0]