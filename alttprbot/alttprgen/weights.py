weights = {
    # this emulates the weights used when picking the daily
    'daily': {
        "description": "Uses the weights currently in use for generating the daily games.",
        "glitches_required": {
            "none": 76,
            "overworld_glitches": 21,
            "major_glitches": 3,
            "no_logic": 0
        },
        "item_placement": {
            "basic": 60,
            "advanced": 40
        },
        "dungeon_items": {
            "standard": 60,
            "mc": 10,
            "mcs": 10,
            "full": 20
        },
        "accessibility": {
            "items": 60,
            "locations": 10,
            "none": 30
        },
        "goals": {
            "ganon": 30,
            "fast_ganon": 40,
            "dungeons": 10,
            "pedestal": 10,
            "triforce-hunt": 10
        },
        "tower_open": {
            "0": 5,
            "1": 5,
            "2": 5,
            "3": 5,
            "4": 5,
            "5": 5,
            "6": 5,
            "7": 50,
            "random": 15
        },
        "ganon_open": {
            "0": 5,
            "1": 5,
            "2": 5,
            "3": 5,
            "4": 5,
            "5": 5,
            "6": 5,
            "7": 50,
            "random": 15
        },
        "world_state": {
            "standard": 20,
            "open": 45,
            "inverted": 25,
            "retro": 10
        },
        "entrance_shuffle": {
            "none": 90,
            "simple": 2,
            "restricted": 2,
            "full": 2,
            "crossed": 2,
            "insanity": 2
        },
        "boss_shuffle": {
            "none": 60,
            "simple": 10,
            "full": 10,
            "random": 20
        },
        "enemy_shuffle": {
            "none": 80,
            "shuffled": 10,
            "random": 10
        },
        "hints": {
            "on": 50,
            "off": 50
        },
        "weapons": {
            "randomized": 60,
            "assured": 10,
            "vanilla": 10,
            "swordless": 10
        },
        "item_pool": {
            "normal": 70,
            "hard": 20,
            "expert": 10,
            "crowd_control": 0
        },
        "item_functionality": {
            "normal": 70,
            "hard": 20,
            "expert": 10
        },
        "enemy_damage": {
            "default": 80,
            "shuffled": 10,
            "random": 10
        },
        "enemy_health": {
            "default": 80,
            "easy": 5,
            "hard": 10,
            "expert": 5
        }
    },
    'friendly': {
        "description": "A friendlier weightset.  Designed for those who don't want something something extreme.",
        "glitches_required": {
            "none": 100,
            "overworld_glitches": 0,
            "major_glitches": 0,
            "no_logic": 0
        },
        "item_placement": {
            "basic": 30,
            "advanced": 70
        },
        "dungeon_items": {
            "standard": 50,
            "mc": 10,
            "mcs": 10,
            "full": 30
        },
        "accessibility": {
            "items": 75,
            "locations": 0,
            "none": 25
        },
        "goals": {
            "ganon": 40,
            "fast_ganon": 20,
            "dungeons": 10,
            "pedestal": 20,
            "triforce-hunt": 10
        },
        "tower_open": {
            "0": 5,
            "1": 5,
            "2": 5,
            "3": 5,
            "4": 5,
            "5": 5,
            "6": 5,
            "7": 50,
            "random": 15
        },
        "ganon_open": {
            "0": 5,
            "1": 5,
            "2": 5,
            "3": 5,
            "4": 5,
            "5": 5,
            "6": 5,
            "7": 50,
            "random": 15
        },
        "world_state": {
            "standard": 35,
            "open": 35,
            "inverted": 20,
            "retro": 10
        },
        "entrance_shuffle": {
            "none": 80,
            "simple": 10,
            "restricted": 5,
            "full": 5,
            "crossed": 0,
            "insanity": 0
        },
        "boss_shuffle": {
            "none": 60,
            "simple": 10,
            "full": 10,
            "random": 20
        },
        "enemy_shuffle": {
            "none": 80,
            "shuffled": 10,
            "random": 10
        },
        "hints": {
            "on": 70,
            "off": 30
        },
        "weapons": {
            "randomized": 40,
            "assured": 40,
            "vanilla": 5,
            "swordless": 5
        },
        "item_pool": {
            "normal": 80,
            "hard": 20,
            "expert": 0,
            "crowd_control": 0
        },
        "item_functionality": {
            "normal": 80,
            "hard": 20,
            "expert": 0
        },
        "enemy_damage": {
            "default": 80,
            "shuffled": 10,
            "random": 10
        },
        "enemy_health": {
            "default": 90,
            "easy": 10,
            "hard": 0,
            "expert": 0
        }
    },
    'weighted': {
        "description": "The default.  Offers every setting, but with some balance.",
        "glitches_required": {
            "none": 100,
            "overworld_glitches": 0,
            "major_glitches": 0,
            "no_logic": 0
        },
        "item_placement": {
            "basic": 25,
            "advanced": 75
        },
        "dungeon_items": {
            "standard": 60,
            "mc": 10,
            "mcs": 10,
            "full": 20
        },
        "accessibility": {
            "items": 60,
            "locations": 10,
            "none": 30
        },
        "goals": {
            "ganon": 40,
            "fast_ganon": 20,
            "dungeons": 10,
            "pedestal": 20,
            "triforce-hunt": 10
        },
        "tower_open": {
            "0": 5,
            "1": 5,
            "2": 5,
            "3": 5,
            "4": 5,
            "5": 5,
            "6": 5,
            "7": 50,
            "random": 15
        },
        "ganon_open": {
            "0": 5,
            "1": 5,
            "2": 5,
            "3": 5,
            "4": 5,
            "5": 5,
            "6": 5,
            "7": 50,
            "random": 15
        },
        "world_state": {
            "standard": 35,
            "open": 35,
            "inverted": 20,
            "retro": 10
        },
        "entrance_shuffle": {
            "none": 60,
            "simple": 7,
            "restricted": 10,
            "full": 10,
            "crossed": 10,
            "insanity": 2
        },
        "boss_shuffle": {
            "none": 60,
            "simple": 10,
            "full": 10,
            "random": 20
        },
        "enemy_shuffle": {
            "none": 60,
            "shuffled": 20,
            "random": 20
        },
        "hints": {
            "on": 50,
            "off": 50
        },
        "weapons": {
            "randomized": 20,
            "assured": 60,
            "vanilla": 15,
            "swordless": 5
        },
        "item_pool": {
            "normal": 80,
            "hard": 15,
            "expert": 5,
            "crowd_control": 0
        },
        "item_functionality": {
            "normal": 80,
            "hard": 15,
            "expert": 5
        },
        "enemy_damage": {
            "default": 80,
            "shuffled": 10,
            "random": 10
        },
        "enemy_health": {
            "default": 80,
            "easy": 5,
            "hard": 10,
            "expert": 5
        }
    },
    'unweighted': {
        "description": "Every option is possible.  GLHF.",
        "glitches_required": {
            "none": 1,
            "overworld_glitches": 0,
            "major_glitches": 0,
            "no_logic": 0
        },
        "item_placement": {
            "basic": 1,
            "advanced": 1
        },
        "dungeon_items": {
            "standard": 1,
            "mc": 1,
            "mcs": 1,
            "full": 1
        },
        "accessibility": {
            "items": 1,
            "locations": 1,
            "none": 1
        },
        "goals": {
            "ganon": 1,
            "fast_ganon": 1,
            "dungeons": 1,
            "pedestal": 1,
            "triforce-hunt": 1
        },
        "tower_open": {
            "0": 1,
            "1": 1,
            "2": 1,
            "3": 1,
            "4": 1,
            "5": 1,
            "6": 1,
            "7": 1,
            "random": 1
        },
        "ganon_open": {
            "0": 1,
            "1": 1,
            "2": 1,
            "3": 1,
            "4": 1,
            "5": 1,
            "6": 1,
            "7": 1,
            "random": 1
        },
        "world_state": {
            "standard": 1,
            "open": 1,
            "inverted": 1,
            "retro": 1
        },
        "entrance_shuffle": {
            "none": 1,
            "simple": 1,
            "restricted": 1,
            "full": 1,
            "crossed": 1,
            "insanity": 1
        },
        "boss_shuffle": {
            "none": 1,
            "simple": 1,
            "full": 1,
            "random": 1
        },
        "enemy_shuffle": {
            "none": 1,
            "shuffled": 1,
            "random": 1
        },
        "hints": {
            "on": 1,
            "off": 1
        },
        "weapons": {
            "randomized": 1,
            "assured": 1,
            "vanilla": 1,
            "swordless": 1
        },
        "item_pool": {
            "normal": 1,
            "hard": 1,
            "expert": 1,
            "crowd_control": 0
        },
        "item_functionality": {
            "normal": 1,
            "hard": 1,
            "expert": 1
        },
        "enemy_damage": {
            "default": 1,
            "shuffled": 1,
            "random": 1
        },
        "enemy_health": {
            "default": 1,
            "easy": 1,
            "hard": 1,
            "expert": 1
        }
    },
    'owg': {
        "description": "This'll always be OWG.  Always.",
        "glitches_required": {
            "none": 0,
            "overworld_glitches": 100,
            "major_glitches": 0,
            "no_logic": 0
        },
        "item_placement": {
            "basic": 25,
            "advanced": 75
        },
        "dungeon_items": {
            "standard": 60,
            "mc": 10,
            "mcs": 10,
            "full": 20
        },
        "accessibility": {
            "items": 70,
            "locations": 0,
            "none": 30
        },
        "goals": {
            "ganon": 40,
            "fast_ganon": 20,
            "dungeons": 10,
            "pedestal": 20,
            "triforce-hunt": 10
        },
        "tower_open": {
            "0": 5,
            "1": 5,
            "2": 5,
            "3": 5,
            "4": 5,
            "5": 5,
            "6": 5,
            "7": 50,
            "random": 15
        },
        "ganon_open": {
            "0": 5,
            "1": 5,
            "2": 5,
            "3": 5,
            "4": 5,
            "5": 5,
            "6": 5,
            "7": 50,
            "random": 15
        },
        "world_state": {
            "standard": 10,
            "open": 70,
            "inverted": 20,
            "retro": 0
        },
        "entrance_shuffle": {
            "none": 100,
            "simple": 0,
            "restricted": 0,
            "full": 0,
            "crossed": 0,
            "insanity": 0
        },
        "boss_shuffle": {
            "none": 60,
            "simple": 10,
            "full": 10,
            "random": 20
        },
        "enemy_shuffle": {
            "none": 60,
            "shuffled": 20,
            "random": 20
        },
        "hints": {
            "on": 50,
            "off": 50
        },
        "weapons": {
            "randomized": 20,
            "assured": 60,
            "vanilla": 15,
            "swordless": 5
        },
        "item_pool": {
            "normal": 80,
            "hard": 15,
            "expert": 5,
            "crowd_control": 0
        },
        "item_functionality": {
            "normal": 80,
            "hard": 15,
            "expert": 5
        },
        "enemy_damage": {
            "default": 80,
            "shuffled": 10,
            "random": 10
        },
        "enemy_health": {
            "default": 80,
            "easy": 5,
            "hard": 10,
            "expert": 5
        }
    },
    'nologic': {
        "description": "Anything can be anywhere and nothing maters anymore.",
        "glitches_required": {
            "none": 0,
            "overworld_glitches": 0,
            "major_glitches": 0,
            "no_logic": 100
        },
        "item_placement": {
            "basic": 25,
            "advanced": 75
        },
        "dungeon_items": {
            "standard": 60,
            "mc": 10,
            "mcs": 10,
            "full": 20
        },
        "accessibility": {
            "items": 0,
            "locations": 0,
            "none": 100
        },
        "goals": {
            "ganon": 40,
            "fast_ganon": 20,
            "dungeons": 10,
            "pedestal": 20,
            "triforce-hunt": 10
        },
        "tower_open": {
            "0": 5,
            "1": 5,
            "2": 5,
            "3": 5,
            "4": 5,
            "5": 5,
            "6": 5,
            "7": 50,
            "random": 15
        },
        "ganon_open": {
            "0": 5,
            "1": 5,
            "2": 5,
            "3": 5,
            "4": 5,
            "5": 5,
            "6": 5,
            "7": 50,
            "random": 15
        },
        "world_state": {
            "standard": 10,
            "open": 70,
            "inverted": 20,
            "retro": 0
        },
        "entrance_shuffle": {
            "none": 100,
            "simple": 0,
            "restricted": 0,
            "full": 0,
            "crossed": 0,
            "insanity": 0
        },
        "boss_shuffle": {
            "none": 60,
            "simple": 10,
            "full": 10,
            "random": 20
        },
        "enemy_shuffle": {
            "none": 60,
            "shuffled": 20,
            "random": 20
        },
        "hints": {
            "on": 50,
            "off": 50
        },
        "weapons": {
            "randomized": 20,
            "assured": 60,
            "vanilla": 15,
            "swordless": 5
        },
        "item_pool": {
            "normal": 80,
            "hard": 15,
            "expert": 5,
            "crowd_control": 0
        },
        "item_functionality": {
            "normal": 80,
            "hard": 15,
            "expert": 5
        },
        "enemy_damage": {
            "default": 80,
            "shuffled": 10,
            "random": 10
        },
        "enemy_health": {
            "default": 80,
            "easy": 5,
            "hard": 10,
            "expert": 5
        }
    },
}
