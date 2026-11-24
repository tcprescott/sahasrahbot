from pyz3r.smvaria import SuperMetroidVaria
from alttprbot.exceptions import InvalidInputError, SeedGenerationError


async def generate_preset(settings, skills, race=False):
    seed = await SuperMetroidVaria.create(
        skills_preset=skills,
        settings_preset=settings,
        race=race
    )
    return seed


AQUEDUCT = 'Aqueduct'
BIG_PINK = 'Big Pink'
BUBBLE_MOUNTAIN = 'Bubble Mountain'
BUSINESS_CENTER = 'Business Center'
ETECOONS_SUPERS = 'Etecoons Supers'
FIREFLEAS_TOP = 'Firefleas Top'
GAUNTLET_TOP = 'Gauntlet Top'
GOLDEN_FOUR = 'Golden Four'
GREEN_BRINSTAR_ELEVATOR = 'Green Brinstar Elevator'
RED_BRINSTAR_ELEVATOR = 'Red Brinstar Elevator'
WRECKED_SHIP_MAIN = 'Wrecked Ship Main'
LANDING_SITE = 'Landing Site'

CHOOZO_SPLITS = {
    "FullCountdown": "FullWithHUD",
    "M/m": "Major",
    "RandomSplit": "random"
}

CHOOZO_AREAS = {
    "FullArea": "full",
    "LightArea": "light",
    "VanillaArea": "off",
}

CHOOZO_BOSSES = ('RandomBoss', 'VanillaBoss')

CHOOZO_DIFFICULTIES = {
    "HarderDifficulty": "harder",
    "HardDifficulty": "hard",
    "MediumDifficulty": "medium",
    "EasyDifficulty": "easy",
    "BasicDifficulty": "easy"
}

CHOOZO_ESCAPES = ('RandomEscape', 'VanillaEscape')

CHOOZO_MORPHS = {
    "LateMorph": "late",
    "RandomMorph": "random",
    "EarlyMorph": "early"
}

CHOOZO_STARTS = {
    "DeepStart": [AQUEDUCT, BUBBLE_MOUNTAIN, FIREFLEAS_TOP],
    "RandomStart": [
        AQUEDUCT, BIG_PINK, BUBBLE_MOUNTAIN, BUSINESS_CENTER, ETECOONS_SUPERS, FIREFLEAS_TOP,
        GAUNTLET_TOP, GOLDEN_FOUR, GREEN_BRINSTAR_ELEVATOR, RED_BRINSTAR_ELEVATOR, WRECKED_SHIP_MAIN,
    ],
    "NotDeepStart": [
        BIG_PINK, BUSINESS_CENTER, ETECOONS_SUPERS, GAUNTLET_TOP, GOLDEN_FOUR,
        GREEN_BRINSTAR_ELEVATOR, RED_BRINSTAR_ELEVATOR, WRECKED_SHIP_MAIN,
    ],
    "ShallowStart": [BIG_PINK, GAUNTLET_TOP, GREEN_BRINSTAR_ELEVATOR, WRECKED_SHIP_MAIN],
    "VanillaStart": [LANDING_SITE],
}


def _require_choice(value, choices, setting):
    """Raise ValueError unless value is one of choices (listed in the message in order)."""
    if value not in choices:
        names = list(choices)
        allowed = ", ".join(names[:-1]) + " or " + names[-1] if len(names) > 2 else " or ".join(names)
        raise ValueError(f"Invalid {setting} setting.  Must be {allowed}.")


async def generate_choozo(ctx, race, split, area, boss, difficulty, escape, morph, start):
    _require_choice(split, CHOOZO_SPLITS, "item split")
    _require_choice(area, CHOOZO_AREAS, "area")
    _require_choice(boss, CHOOZO_BOSSES, "boss")
    _require_choice(difficulty, CHOOZO_DIFFICULTIES, "difficulty")
    _require_choice(escape, CHOOZO_ESCAPES, "escape")
    _require_choice(morph, CHOOZO_MORPHS, "morph")
    _require_choice(start, CHOOZO_STARTS, "start")

    settings = {
        "hud": "on",
        "suitsRestriction": "off",
        "variaTweaks": "on",

        "majorsSplit": CHOOZO_SPLITS[split],
        "majorsSplitMultiSelect": ['FullWithHUD', 'Major'],

        "areaRandomization": CHOOZO_AREAS[area],
        "areaLayout": "off" if area == "VanillaArea" else "on",

        "bossRandomization": "off" if boss == "VanillaBoss" else "on",

        "maxDifficulty": CHOOZO_DIFFICULTIES[difficulty],

        "escapeRando": "off" if escape == "VanillaEscape" else "on",

        "morphPlacement": CHOOZO_MORPHS[morph],

        "startLocation": LANDING_SITE if start == "VanillaStart" else "random",
        "startLocationMultiSelect": CHOOZO_STARTS[start]
    }

    await ctx.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")
    seed = await SuperMetroidVaria.create(
        settings_preset="Season_Races",
        skills_preset="newbie" if difficulty == "BasicDifficulty" else "Season_Races",
        race=race,
        settings_dict=settings,
        raise_for_status=False
    )
    if not hasattr(seed, 'guid'):
        raise SeedGenerationError("Error: %s" % seed.data)
    return seed


async def generate_league_playoff(majors, area, bosses):
    if majors not in ['FullTraditional', 'FullRandom', 'Major', 'Chozo']:
        raise InvalidInputError("Invalid major setting. Must be FullTraditional, FullRandom, Major, or Chozo.")

    if area not in ['Off', 'Light', 'Full']:
        raise InvalidInputError("Invalid area setting.  Must be Off, Light, or Full.")

    if bosses not in ['Off', 'On']:
        raise InvalidInputError("Invalid bosses setting.  Must be Off, or On.")

    settings = {
        "majorsSplit": "Full" if majors in ['FullTraditional', 'FullRandom'] else majors,

        # these are both set at same time
        "areaRandomization": "off" if area == "Off" else "on",
        "areaLayout": "off" if area == "Off" else "on",

        # requires area rando on
        "lightAreaRandomization": "on" if area == "Light" else "off",

        # boss rando
        "bossRandomization": "off" if bosses == "Off" else "on",
    }
    if majors == "FullRandom":
        settings['startLocation'] = 'random'
        settings['startLocationMultiSelect'] = [
            'Gauntlet Top',
            'Green Brinstar Elevator',
            'Big Pink,Etecoons Supers',
            'Wrecked Ship Main',
            'Firefleas Top',
            'Business Center',
            'Bubble Mountain',
            'Mama Turtle'
        ]

    seed = await SuperMetroidVaria.create(
        settings_preset="Season_Races",
        skills_preset="Season_Races",
        settings_dict=settings,
        race=True
    )
    return seed
