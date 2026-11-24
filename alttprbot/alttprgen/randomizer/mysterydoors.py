import copy
import logging
from dataclasses import dataclass
import random

from pyz3r.mystery import get_random_option, generate_random_settings

from alttprbot.alttprgen.randomizer.alttpr import ALTTPRClient
from alttprbot.alttprgen.randomizer.alttprdoor import AlttprDoor


@dataclass
class AlttprMystery:
    weights: dict
    settings: dict
    customizer: bool = False
    doors: bool = False
    custom_instructions: str | None = None
    seed: AlttprDoor | ALTTPRClient | None = None
    branch: str | None = None


BASE_DOORS_PAYLOAD = {
    "retro": False,
    "mode": "open",
    "logic": "noglitches",
    "goal": "ganon",
    "crystals_gt": "7",
    "crystals_ganon": "7",
    "swords": "random",
    "difficulty": "normal",
    "item_functionality": "normal",
    "accessibility": "items",
    "algorithm": "balanced",

    # Shuffle Ganon defaults to TRUE
    "openpyramid": False,
    "shuffleganon": True,
    "shuffle": "vanilla",

    "shufflepots": False,
    "shuffleenemies": "none",
    "shufflebosses": "none",
    "enemy_damage": "default",
    "enemy_health": "default",
    "keydropshuffle": False,
    "dropshuffle": False,
    "pottery": "none",
    "colorizepots": False,
    "mapshuffle": False,
    "compassshuffle": False,
    "keyshuffle": False,
    "bigkeyshuffle": False,
    "keysanity": False,
    "timer": "none",
    "door_shuffle": "vanilla",
    "intensity": 2,
    "experimental": False,
    "dungeon_counters": "default",
    "collection_rate": False,
    "bombbag": False,
    "triforce_pool": 0,
    "triforce_goal": 0,
    "restrict_boss_items": "none",
    "shufflelinks": False,
    "overworld_map": "default",
    "pseudoboots": False,
    "hints": True,
    "startinventory": "",
    "beemizer": 0,
    "startinventoryarray": {}
}


def _roll_start_inventory(weights):
    """Roll the starting items, capped at a random sample of startinventorylimit."""
    inventoryweights: dict = weights.get('startinventory', {})

    startinventory_limit = get_random_option(weights.get('startinventorylimit', None))

    startitems = []
    for item in inventoryweights:
        count = get_random_option(weights['startinventory'][item])
        if count > 0:
            startitems += count * [item]

    # if we have a startinventory limit, limit the number of items by random sampling
    if startinventory_limit is not None and len(startitems) > startinventory_limit:
        startitems = random.sample(startitems, k=startinventory_limit)
    return startitems


def _force_assured_swords(options):
    # This is dedicated to the survivors of http://www.speedrunslive.com/races/result/#!/264658
    # Play https://alttpr.com/en/h/30yAqZ99yV if you don't believe me. <3
    enemizer = (options['enemy_shuffle'] != 'none' or options['enemy_damage'] != 'default'
                or options['enemy_health'] != 'default')
    if options['weapons'] not in ['vanilla', 'assured'] and options['world_state'] == 'standard' and enemizer:
        options['weapons'] = 'assured'


def _rule_matches(rule, options):
    """True when every exact-match condition of the rule holds (other match types are ignored)."""
    return all(
        options[condition['Key']] == condition['Value']
        for condition in rule.get('conditions', {})
        if condition.get('MatchType', 'exact') == 'exact'
    )


def _apply_rules(weights, options):
    for rule in weights.get('rules', {}):
        if _rule_matches(rule, options):
            for key, value in rule.get('actions', {}).items():
                options[key] = get_random_option(value)


# setting -> (dungeon_items values that turn it on when the weights don't roll it directly)
_DUNGEON_ITEM_DEFAULTS = {
    "mapshuffle": ('mc', 'mcs', 'full'),
    "compassshuffle": ('mc', 'mcs', 'full'),
    "keyshuffle": ('mcs', 'full'),
    "bigkeyshuffle": ('full',),
    "keysanity": ('full',),
}


def _dungeon_item_settings(weights, options):
    return {
        setting: options[setting] == 'on' if setting in weights else options['dungeon_items'] in on_for
        for setting, on_for in _DUNGEON_ITEM_DEFAULTS.items()
    }


def generate_doors_settings(weights, options):
    branch = weights.get('options', {}).get('branch', 'stable')

    options["glitches"] = get_random_option(weights['glitches_required'])
    options["dungeon_items"] = get_random_option(weights['dungeon_items'])
    options["accessibility"] = get_random_option(weights['accessibility'])
    options["goals"] = get_random_option(weights['goals'])
    options["ganon_open"] = get_random_option(weights['ganon_open'])
    options["tower_open"] = get_random_option(weights['tower_open'])
    options["world_state"] = get_random_option(weights['world_state'])
    options["hints"] = get_random_option(weights['hints'])
    options["weapons"] = get_random_option(weights['weapons'])
    options["item_pool"] = get_random_option(weights['item_pool'])
    options["item_functionality"] = get_random_option(weights['item_functionality'])
    options["boss_shuffle"] = get_random_option(weights['boss_shuffle'])
    options["enemy_shuffle"] = get_random_option(weights['enemy_shuffle'])
    options["enemy_damage"] = get_random_option(weights['enemy_damage'])
    options["enemy_health"] = get_random_option(weights['enemy_health'])
    options["pot_shuffle"] = get_random_option(weights.get('pot_shuffle', 'off'))
    options['algorithm'] = get_random_option(weights.get('algorithm', 'balanced'))
    options['entrance_shuffle'] = get_random_option(weights['entrance_shuffle'])
    options['colorizepots'] = get_random_option(weights.get('colorizepots', False))

    options["mapshuffle"] = get_random_option(weights.get('mapshuffle', False))
    options["compassshuffle"] = get_random_option(weights.get('compassshuffle', False))
    options["keyshuffle"] = get_random_option(weights.get('keyshuffle', False))
    options["bigkeyshuffle"] = get_random_option(weights.get('bigkeyshuffle', False))

    options["timer"] = get_random_option(weights.get('timer', 'none'))
    options["experimental"] = get_random_option(weights.get('experimental', False))
    options["dungeon_counters"] = get_random_option(weights.get('dungeon_counters', 'default'))
    options["triforce_pool"] = get_random_option(weights.get('triforce_pool', 0))
    options["triforce_goal"] = get_random_option(weights.get('triforce_goal', 0))
    options["restrict_boss_items"] = get_random_option(weights.get('restrict_boss_items', 'none'))
    options["shufflelinks"] = get_random_option(weights.get('shufflelinks', False))
    options["overworld_map"] = get_random_option(weights.get('overworld_map', 'default'))
    options["pseudoboots"] = get_random_option(weights.get('pseudoboots', False))

    options['intensity'] = get_random_option(weights.get('intensity', 2))
    options['beemizer'] = get_random_option(weights.get('beemizer', 0))

    # volatile settings
    if branch == "volatile":
        options["keyshuffle"] = get_random_option(weights.get('keyshuffle', "none"))
        options["dropshuffle"] = get_random_option(weights.get('dropshuffle', "none"))

    startitems = _roll_start_inventory(weights)
    options['startinventory'] = ','.join(startitems)

    _force_assured_swords(options)
    _apply_rules(weights, options)

    settings = copy.deepcopy(BASE_DOORS_PAYLOAD)

    settings["retro"] = options['world_state'] == 'retro'
    settings["mode"] = "open" if options['world_state'] == 'retro' else options['world_state']

    settings["logic"] = "noglitches"

    door_goals = {'fast_ganon': 'crystals', 'triforce-hunt': 'triforcehunt'}
    settings["goal"] = door_goals.get(options['goals'], options['goals'])

    settings["crystals_gt"] = options['tower_open']
    settings["crystals_ganon"] = options['ganon_open']
    settings["swords"] = {'randomized': 'random',
                          'assured': 'assured',
                          'vanilla': 'vanilla',
                          'swordless': 'swordless'
                          }[options['weapons']]
    settings["difficulty"] = options['item_pool']
    settings["item_functionality"] = options['item_functionality']
    settings["accessibility"] = options['accessibility']
    settings["shopsanity"] = options['shopsanity'] == 'on'
    settings["algorithm"] = options['algorithm']
    settings["shuffleganon"] = True
    settings["shuffle"] = "vanilla" if options['entrance_shuffle'] == "none" else options['entrance_shuffle']
    settings["openpyramid"] = (settings['shuffle'] in ['vanilla', 'dungeonsfull', 'dungeonssimple']
                               and settings['goal'] in ['crystals', 'trinity'])
    settings["shufflepots"] = options['pot_shuffle'] == 'on'
    settings["shuffleenemies"] = options['enemy_shuffle']
    settings["shufflebosses"] = options['boss_shuffle']
    settings["enemy_damage"] = options['enemy_damage']
    settings["enemy_health"] = options['enemy_health']
    settings["keydropshuffle"] = options['keydropshuffle'] == 'on'
    settings["dropshuffle"] = options['dropshuffle'] == 'on'
    settings["pottery"] = options['pottery']
    settings["colorizepots"] = options['colorizepots'] == 'on'

    settings.update(_dungeon_item_settings(weights, options))

    settings["timer"] = options["timer"]
    settings["experimental"] = options['experimental'] == 'on'
    settings["dungeon_counters"] = options["dungeon_counters"]
    settings["collection_rate"] = options["collection_rate"]
    settings["bombbag"] = options["bombbag"]
    settings["triforce_pool"] = options["triforce_pool"]
    settings["triforce_goal"] = options["triforce_goal"]
    settings["restrict_boss_items"] = options["restrict_boss_items"]
    settings["shufflelinks"] = options["shufflelinks"]
    settings["overworld_map"] = options["overworld_map"]
    settings["pseudoboots"] = options["pseudoboots"]

    settings["door_shuffle"] = options['door_shuffle']
    settings["intensity"] = options['intensity']
    settings["hints"] = options['hints'] == 'on'
    settings["beemizer"] = options['beemizer']
    settings["startinventory"] = options['startinventory']
    settings["usestartinventory"] = len(startitems) > 0

    # volatile settings
    if branch == "volatile":
        settings["keyshuffle"] = options["keyshuffle"]
        settings["dropshuffle"] = options["dropshuffle"]

    return settings


def generate_doors_mystery(weights, tournament=True, spoilers="mystery"):
    while True:
        subweight_name = get_random_option(
            {k: v['chance'] for (k, v) in weights.get('subweights', {}).items()})

        logging.info(f"{subweight_name=}")

        if subweight_name is None:
            break

        subweights = weights.get('subweights', {}).get(subweight_name, {}).get('weights', {})
        subweights['subweights'] = subweights.get('subweights', {})
        weights = {**weights, **subweights}

    options = {}
    options['door_shuffle'] = get_random_option(weights.get('door_shuffle', 'vanilla'))
    options['keydropshuffle'] = get_random_option(weights.get('keydropshuffle', False))
    options['dropshuffle'] = get_random_option(weights.get('dropshuffle', False))
    options['pottery'] = get_random_option(weights.get('pottery', 'none'))
    options['shopsanity'] = get_random_option(weights.get('shopsanity', False))
    options["collection_rate"] = get_random_option(weights.get('collection_rate', False))
    options["bombbag"] = get_random_option(weights.get('bombbag', False))

    doors = options['door_shuffle'] != 'vanilla'
    somedropshuffle = options['keydropshuffle'] == 'on' or options['dropshuffle'] == 'on' or options[
        'pottery'] != 'none'
    shopsanity = options['shopsanity'] == 'on'
    collection_rate = options['collection_rate'] == 'on'
    bombbag = options['bombbag'] == 'on'

    custom_instructions = get_random_option(weights.get('custom_instructions', None))

    if doors or somedropshuffle or shopsanity or collection_rate or bombbag or weights.get('options', {}).get(
            'force_doors', False):
        settings = generate_doors_settings(weights, options)
        customizer = False
        doors = True
        branch = weights.get('options', {}).get('branch', 'stable')
    else:
        settings, customizer = generate_random_settings(weights, tournament=tournament, spoilers=spoilers)
        doors = False
        branch = None

    return AlttprMystery(
        weights=weights,
        settings=settings,
        customizer=customizer,
        doors=doors,
        custom_instructions=custom_instructions,
        branch=branch
    )
