import json
import random
import string
from collections import OrderedDict

import aiofiles
import pyz3r.misc

from config import Config as c

from .preset import get_preset


async def generate_spoiler_game(preset):
    seed, preset_dict = await get_preset(preset, hints=False, spoilers_ongen=True)
    if not seed:
        return False, False, False
    spoiler_log_url = await write_json_to_disk(seed)
    return seed, preset_dict, spoiler_log_url

async def write_json_to_disk(seed):
    code = await seed.code()
    filename = f"spoiler__{seed.hash}__{'-'.join(code).replace(' ', '')}__{''.join(random.choices(string.ascii_letters + string.digits, k=4))}.txt"

    # magic happens here to make it pretty-printed and tournament-compliant
    s = seed.data['spoiler']
    try:
        del s['playthrough']
    except KeyError:
        pass

    # if seed.meta['meta'][]
    # try:
    #     del s['Shops'] #QOL this information is useless for this tournament
    # except KeyError:
    #     pass

    # if seed.data['meta']['enemizer.boss_shuffle'] == 'none':
    #     try:
    #         del s['Bosses'] #QOL this information is useful only for enemizer
    #     except KeyError:
    #         pass

    sorteddict = OrderedDict() 

    if not 'shuffle' in s['meta']:
        sectionlist = [
            'Special',
            'Hyrule Castle',
            'Eastern Palace',
            'Desert Palace',
            'Tower Of Hera',
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
        prizemap = [
            ['Eastern Palace', 'Eastern Palace - Prize:1'],
            ['Desert Palace', 'Desert Palace - Prize:1'],
            ['Tower Of Hera', 'Tower of Hera - Prize:1'],
            ['Dark Palace', 'Palace of Darkness - Prize:1'],
            ['Swamp Palace', 'Swamp Palace - Prize:1'],
            ['Skull Woods', 'Skull Woods - Prize:1'],
            ['Thieves Town', 'Thieves\' Town - Prize:1'],
            ['Ice Palace', 'Ice Palace - Prize:1'],
            ['Misery Mire', 'Misery Mire - Prize:1'],
            ['Turtle Rock', 'Turtle Rock - Prize:1'],
        ]
    else:
        sectionlist = [
            'Special',
            'Hyrule Castle',
            'Eastern Palace',
            'Desert Palace',
            'Tower of Hera',
            'Palace of Darkness',
            'Swamp Palace',
            'Skull Woods',
            'Thieves Town',
            'Ice Palace',
            'Misery Mire',
            'Turtle Rock',
            'Ganons Tower',
            'Caves',
            'Light World',
            'Dark World'
        ]
        prizemap = [
            ['Eastern Palace', 'Eastern Palace - Prize'],
            ['Desert Palace', 'Desert Palace - Prize'],
            ['Tower of Hera', 'Tower of Hera - Prize'],
            ['Palace of Darkness', 'Palace of Darkness - Prize'],
            ['Swamp Palace', 'Swamp Palace - Prize'],
            ['Skull Woods', 'Skull Woods - Prize'],
            ['Thieves Town', 'Thieves\' Town - Prize'],
            ['Ice Palace', 'Ice Palace - Prize'],
            ['Misery Mire', 'Misery Mire - Prize'],
            ['Turtle Rock', 'Turtle Rock - Prize'],
        ]
    sorteddict['Prizes'] = {}
    for dungeon, prize in prizemap:
        sorteddict['Prizes'][dungeon] = s[dungeon][prize].replace(':1','')

    for section in sectionlist:
        sorteddict[section] = mw_filter(s[section])

    drops = get_seed_prizepacks(seed.data)
    sorteddict['Drops'] = {}
    sorteddict['Drops']['PullTree'] = drops['PullTree']
    sorteddict['Drops']['RupeeCrab'] = {}
    sorteddict['Drops']['RupeeCrab']['Main'] = drops['RupeeCrab']['Main']
    sorteddict['Drops']['RupeeCrab']['Final'] = drops['RupeeCrab']['Final']
    sorteddict['Drops']['Stun'] = drops['Stun']
    sorteddict['Drops']['FishSave'] = drops['FishSave']

    sorteddict['Special']['DiggingGameDigs'] = pyz3r.misc.misc.seek_patch_data(seed.data['patch'], 982421, 1)[0]

    if s['meta']['mode'] == 'retro':
        sorteddict['Shops'] = s['Shops']

    if not s['meta']['enemizer.boss_shuffle'] == 'none':
        sorteddict['Bosses'] = mw_filter(s['Bosses'])

    if 'shuffle' in s['meta'] and not s['meta']['shuffle'] == 'none':
        sorteddict['Entrances'] = s['Entrances']

    sorteddict['meta']           = s['meta']
    sorteddict['meta']['hash']   = seed.hash
    sorteddict['meta']['permalink'] = seed.url

    for dungeon, prize in prizemap:
        del sorteddict[dungeon][prize.replace(':1','')]

    async with aiofiles.open(f"{c.SpoilerLogLocal}/{filename}", "w+", newline='\r\n') as out:
        await out.write(json.dumps(sorteddict, indent=4))
        await out.flush()

    # async with aiofiles.open(f"{c.SpoilerLogLocal}/{filename}", "w+", newline='\r\n') as out:
    #     dump = yaml.dump(sorteddict)
    #     await out.write(dump)

    return c.SpoilerLogUrlBase + '/' + filename

def get_seed_prizepacks(data):
    d = {}
    d['PullTree'] = {}
    d['RupeeCrab'] = {}

    stun_offset = '227731'
    pulltree_offset = '981972'
    rupeecrap_main_offset = '207304'
    rupeecrab_final_offset = '207300'
    fishsave_offset = '950988'

    for patch in data['patch']:
        if stun_offset in patch:
            d['Stun'] = get_sprite_droppable(patch[stun_offset][0])
        if pulltree_offset in patch:
            d['PullTree']['Tier1'] = get_sprite_droppable(patch[pulltree_offset][0])
            d['PullTree']['Tier2'] = get_sprite_droppable(patch[pulltree_offset][1])
            d['PullTree']['Tier3'] = get_sprite_droppable(patch[pulltree_offset][2])
        if rupeecrap_main_offset in patch:
            d['RupeeCrab']['Main'] = get_sprite_droppable(patch[rupeecrap_main_offset][0])
        if rupeecrab_final_offset in patch:
            d['RupeeCrab']['Final'] = get_sprite_droppable(patch[rupeecrab_final_offset][0])
        if fishsave_offset in patch:
            d['FishSave'] = get_sprite_droppable(patch[fishsave_offset][0])
    
    return d

def get_sprite_droppable(i):
    spritemap = {
        121: "Bee", 178: "BeeGood", 216: "Heart",
        217: "RupeeGreen", 218: "RupeeBlue", 219: "RupeeRed",
        220: "BombRefill1", 221: "BombRefill4", 222: "BombRefill8",
        223: "MagicRefillSmall", 224: "MagicRefillFull",
        225: "ArrowRefill5", 226: "ArrowRefill10",
        227: "Fairy",
    }
    try: return spritemap[i]
    except KeyError: return 'ERR: UNKNOWN'

# def mw_filter(dict):
#     sorteddict = {}
#     for key in sorted(dict):
#         sorteddict[key] = dict[key]
#     return sorteddict

def mw_filter(dict):
    sorteddict = {}
    for key, item in dict.items():
        sorteddict[key.replace(':1','')] = dict[key].replace(':1','')
    return sorteddict