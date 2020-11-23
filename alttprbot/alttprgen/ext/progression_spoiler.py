from collections import OrderedDict
from pyz3r.spoiler import mw_filter

REGIONLIST = [
    'Hyrule Castle',
    'Eastern Palace',
    'Desert Palace',
    'Tower Of Hera',
    'Castle Tower',
    'Dark Palace',
    'Swamp Palace',
    'Skull Woods',
    'Thieves Town',
    'Ice Palace',
    'Misery Mire',
    'Turtle Rock',
    'Ganons Tower',
    'Light World',
    'Death Mountain',
    'Dark World'
]

PROGRESSION_ITEMS = [
    'L1Sword',
    'MasterSword',
    'ProgressiveSword',
    # 'BossHeartContainer',
    'BottleWithRandom',
    'Bottle',
    'BottleWithRedPotion',
    'BottleWithGreenPotion',
    'BottleWithBluePotion',
    'BottleWithBee',
    'BottleWithGoldBee',
    'BottleWithFairy',
    'Bombos',
    'BookOfMudora',
    'BowAndArrows',
    'CaneOfSomaria',
    'Cape',
    'Ether',
    'FireRod',
    'Flippers',
    'Hammer',
    'Hookshot',
    'IceRod',
    'Lamp',
    'MagicMirror',
    'MoonPearl',
    'Mushroom',
    'OcarinaInactive',
    'OcarinaActive',
    'PegasusBoots',
    'Powder',
    'PowerGlove',
    'Quake',
    'Shovel',
    'TitansMitt',
    'BowAndSilverArrows',
    'SilverArrowUpgrade',
    'ProgressiveGlove',
    'ProgressiveBow',
    # 'TriforcePiece',
    # 'PowerStar',
    'BugCatchingNet',
    # 'MirrorShield',
    # 'ProgressiveShield',
    'CaneOfByrna',
    # 'TenBombs',
    # 'HalfMagic',
    # 'QuarterMagic'
]


def create_progression_spoiler(seed):
    if not seed.data['spoiler']['meta'].get('spoilers') in ['on', 'generate']:
        return None

    spoiler = seed.data['spoiler']

    if spoiler['meta'].get('shuffle', 'none') != 'none':
        raise Exception("Entrance randomizer is not yet supported.")

    progression_spoiler = OrderedDict()

    for region in REGIONLIST:
        progression_for_region = [loc for loc, item in mw_filter(
            spoiler[region]).items() if item in PROGRESSION_ITEMS]
        if progression_for_region:
            progression_spoiler[region] = progression_for_region

    progression_spoiler['meta'] = spoiler['meta']
    progression_spoiler['meta']['hash'] = seed.hash
    progression_spoiler['meta']['permalink'] = seed.url

    return progression_spoiler
