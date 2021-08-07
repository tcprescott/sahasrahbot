import copy
import logging

from pyz3r.mystery import get_random_option, generate_random_settings

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
    "mapshuffle": False,
    "compassshuffle": False,
    "keyshuffle": False,
    "bigkeyshuffle": False,
    "keysanity": False,
    "door_shuffle": "basic",
    "intensity": 2,
    "hints": True,
    "startinventory": "",
    "beemizer": 0,
    "startinventoryarray": {}
}


def generate_doors_settings(weights, options):
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
    options['entrance_shuffle'] = get_random_option(weights['entrance_shuffle'])

    options["mapshuffle"] = get_random_option(weights.get('mapshuffle', False))
    options["compassshuffle"] = get_random_option(weights.get('compassshuffle', False))
    options["keyshuffle"] = get_random_option(weights.get('keyshuffle', False))
    options["bigkeyshuffle"] = get_random_option(weights.get('bigkeyshuffle', False))

    options["timer"] = get_random_option(weights.get('timer', 'none'))
    options["dungeon_counters"] = get_random_option(weights.get('dungeon_counters', 'default'))
    options["pseudoboots"] = get_random_option(weights.get('pseudoboots', False))

    options['intensity'] = get_random_option(weights.get('intensity', 2))
    options['beemizer'] = get_random_option(weights.get('beemizer', 0))

    inventoryweights = weights.get('startinventory', {})
    startitems = []
    for item in inventoryweights:
        count = get_random_option(weights['startinventory'][item])
        if count > 0:
            startitems += count * [item]
    options['startinventory'] = ','.join(startitems)

    # This if statement is dedicated to the survivors of http://www.speedrunslive.com/races/result/#!/264658
    # Play https://alttpr.com/en/h/30yAqZ99yV if you don't believe me. <3
    if options['weapons'] not in ['vanilla', 'assured'] and options['world_state'] == 'standard' and (
            options['enemy_shuffle'] != 'none'
            or options['enemy_damage'] != 'default'
            or options['enemy_health'] != 'default'):
        options['weapons'] = 'assured'

    # apply rules
    for rule in weights.get('rules', {}):
        conditions = rule.get('conditions', {})
        actions = rule.get('actions', {})

        # iterate through each condition
        match = True

        for condition in conditions:
            if condition.get('MatchType', 'exact') == 'exact':
                if options[condition['Key']] == condition['Value']:
                    continue
                else:
                    match = False

        if match:
            for key, value in actions.items():
                options[key] = get_random_option(value)

    settings = copy.deepcopy(BASE_DOORS_PAYLOAD)

    settings["retro"] = options['world_state'] == 'retro'
    settings["mode"] = "open" if options['world_state'] == 'retro' else options['world_state']

    settings["logic"] = "noglitches"

    settings["goal"] = {
        'ganon': 'ganon',
        'fast_ganon': 'crystals',
        'dungeons': 'dungeons',
        'pedestal': 'pedestal',
        'triforce-hunt': 'triforcehunt'}[options['goals']]

    settings["crystals_gt"] = options['tower_open']
    settings["crystals_ganon"] = options['tower_open']
    settings["swords"] = {'randomized': 'random',
                            'assured': 'assured',
                            'vanilla': 'vanilla',
                            'swordless': 'swordless'
                            }[options['weapons']]
    settings["difficulty"] = options['item_pool']
    settings["item_functionality"] = options['item_functionality']
    settings["accessibility"] = options['accessibility']
    settings["openpyramid"] = options['goals'] == 'fast_ganon' if options['entrance_shuffle'] in ['vanilla', 'dungeonsfull', 'dungeonssimple'] else False
    settings["shopsanity"] = options['shopsanity'] == 'on'
    settings["shuffleganon"] = True
    settings["shuffle"] = "vanilla" if options['entrance_shuffle'] == "none" else options['entrance_shuffle']
    settings["shufflepots"] = options['pot_shuffle'] == 'on'
    settings["shuffleenemies"] = {'none': 'none',
                          'shuffled': 'shuffled',
                          'random': 'chaos'
                          }[options['enemy_shuffle']]
    settings["shufflebosses"] = options['boss_shuffle']
    settings["enemy_damage"] = {'default': 'default',
                        'shuffled': 'shuffled',
                        'random': 'chaos'
                        }[options['enemy_damage']]
    settings["enemy_health"] = options['enemy_health']
    settings["keydropshuffle"] = options['keydropshuffle'] == 'on'

    settings["mapshuffle"] = options['mapshuffle'] == 'on' if 'mapshuffle' in weights else options['dungeon_items'] in ['mc', 'mcs', 'full']
    settings["compassshuffle"] = options['compassshuffle'] == 'on' if 'compassshuffle' in weights else options['dungeon_items'] in ['mc', 'mcs', 'full']
    settings["keyshuffle"] = options['keyshuffle'] == 'on' if 'keyshuffle' in weights else options['dungeon_items'] in ['mcs', 'full']
    settings["bigkeyshuffle"] = options['bigkeyshuffle'] == 'on' if 'bigkeyshuffle' in weights else options['dungeon_items'] == 'full'
    settings["keysanity"] = options['keysanity'] == 'on' if 'keysanity' in weights else options['dungeon_items'] == 'full'

    settings["timer"] = options["timer"]
    settings["dungeon_counters"] = options["dungeon_counters"]
    settings["pseudoboots"] = options["pseudoboots"]

    settings["door_shuffle"] = options['door_shuffle']
    settings["intensity"] = options['intensity']
    settings["hints"] = options['hints'] == 'on'
    settings["beemizer"] = options['beemizer']
    settings["startinventory"] = options['startinventory']
    settings["usestartinventory"] = len(startitems) > 0

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
    options['shopsanity'] = get_random_option(weights.get('shopsanity', False))

    doors = options['door_shuffle'] != 'vanilla'
    keydropshuffle = options['keydropshuffle'] == 'on'
    shopsanity = options['shopsanity'] == 'on'

    if doors or keydropshuffle or shopsanity or weights.get('options', {}).get('force_doors', False):
        settings = generate_doors_settings(weights, options)
        return settings, False, True

    settings, customizer = generate_random_settings(weights, tournament=tournament, spoilers=spoilers)
    return settings, customizer, False
