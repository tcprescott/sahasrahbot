from alttprbot_discord.util.smvaria_discord import SuperMetroidVariaDiscord


async def generate_preset(settings, skills, race=False):
    seed = await SuperMetroidVariaDiscord.create(
        skills_preset=skills,
        settings_preset=settings,
        race=race
    )
    return seed


async def generate_choozo(ctx, race, split, area, boss, difficulty, escape, morph, start):
    if split not in ['FullCountdown', 'M/m', 'RandomSplit']:
        raise ValueError("Invalid item split setting.  Must be FullCountdown, M/m or RandomSplit.")

    if area not in ['FullArea', 'LightArea', 'VanillaArea']:
        raise ValueError("Invalid area setting.  Must be FullArea, LightArea or VanillaArea.")

    if boss not in ['RandomBoss', 'VanillaBoss']:
        raise ValueError("Invalid boss setting.  Must be RandomBoss or VanillaBoss.")

    if difficulty not in ['HarderDifficulty', 'HardDifficulty', 'MediumDifficulty', 'EasyDifficulty',
                          'BasicDifficulty']:
        raise ValueError(
            "Invalid difficulty setting.  Must be HarderDifficulty, HardDifficulty, MediumDifficulty, EasyDifficulty or BasicDifficulty.")

    if escape not in ['RandomEscape', 'VanillaEscape']:
        raise ValueError("Invalid escape setting.  Must be RandomEscape or VanillaEscape.")

    if morph not in ['LateMorph', 'RandomMorph', 'EarlyMorph']:
        raise ValueError("Invalid morph setting.  Must be LateMorph, RandomMorph or EarlyMorph.")

    if start not in ['DeepStart', 'RandomStart', 'NotDeepStart', 'ShallowStart', 'VanillaStart']:
        raise ValueError(
            "Invalid start setting.  Must be DeepStart, RandomStart, NotDeepStart, ShallowStart or VanillaStart.")

    splitDict = {
        "FullCountdown": "FullWithHUD",
        "M/m": "Major",
        "RandomSplit": "random"
    }

    difficultyDict = {
        "HarderDifficulty": "harder",
        "HardDifficulty": "hard",
        "MediumDifficulty": "medium",
        "EasyDifficulty": "easy",
        "BasicDifficulty": "easy"
    }

    morphDict = {
        "LateMorph": "late",
        "RandomMorph": "random",
        "EarlyMorph": "early"
    }

    startDict = {
        "DeepStart": [
            'Aqueduct',
            'Bubble Mountain',
            'Firefleas Top'
        ],
        "RandomStart": [
            'Aqueduct',
            'Big Pink',
            'Bubble Mountain',
            'Business Center',
            'Etecoons Supers',
            'Firefleas Top',
            'Gauntlet Top',
            'Golden Four',
            'Green Brinstar Elevator',
            'Red Brinstar Elevator',
            'Wrecked Ship Main'
        ],
        "NotDeepStart": [
            'Big Pink',
            'Business Center',
            'Etecoons Supers',
            'Gauntlet Top',
            'Golden Four',
            'Green Brinstar Elevator',
            'Red Brinstar Elevator',
            'Wrecked Ship Main'
        ],
        "ShallowStart": [
            'Big Pink',
            'Gauntlet Top',
            'Green Brinstar Elevator',
            'Wrecked Ship Main'
        ],
        "VanillaStart": [
            'Landing Site'
        ]
    }

    settings = {
        "hud": "on",
        "suitsRestriction": "off",
        "variaTweaks": "on",

        "majorsSplit": splitDict[split],
        "majorsSplitMultiSelect": ['FullWithHUD', 'Major'],

        "areaRandomization": "full" if area == "FullArea" else "light" if area == "LightArea" else "off",
        "areaLayout": "off" if area == "VanillaArea" else "on",

        "bossRandomization": "off" if boss == "VanillaBoss" else "on",

        "maxDifficulty": difficultyDict[difficulty],

        "escapeRando": "off" if escape == "VanillaEscape" else "on",

        "morphPlacement": morphDict[morph],

        "startLocation": "Landing Site" if start == "VanillaStart" else "random",
        "startLocationMultiSelect": startDict[start]
    }

    await ctx.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")
    seed = await SuperMetroidVariaDiscord.create(
        settings_preset="Season_Races",
        skills_preset="newbie" if difficulty == "BasicDifficulty" else "Season_Races",
        race=race,
        settings_dict=settings,
        raise_for_status=False
    )
    if not hasattr(seed, 'guid'):
        raise Exception("Error: %s" % seed.data)
    return seed


async def generate_league_playoff(majors, area, bosses):
    if majors not in ['FullTraditional', 'FullRandom', 'Major', 'Chozo']:
        raise Exception("Invalid major setting. Must be FullTraditional, FullRandom, Major, or Chozo.")

    if area not in ['Off', 'Light', 'Full']:
        raise Exception("Invalid area setting.  Must be Off, Light, or Full.")

    if bosses not in ['Off', 'On']:
        raise Exception("Invalid bosses setting.  Must be Off, or On.")

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

    seed = await SuperMetroidVariaDiscord.create(
        settings_preset="Season_Races",
        skills_preset="Season_Races",
        settings_dict=settings,
        race=True
    )
    return seed
