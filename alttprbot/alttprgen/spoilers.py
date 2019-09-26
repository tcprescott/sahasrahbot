import aiofiles
import json
import pyz3r.misc
import random, string

from .preset import get_preset

from config import Config as c

async def generate_spoiler_game(preset):
    seed, goal_name = await get_preset(preset, hints=False, spoilers_ongen=True)
    if not seed:
        return False, False, False
    spoiler_log_url = await write_json_to_disk(seed)
    return seed, goal_name, spoiler_log_url

async def write_json_to_disk(seed):
    code = await seed.code()
    filename = f"spoiler__{seed.hash}__{'-'.join(code).replace(' ', '')}__{''.join(random.choices(string.ascii_letters + string.digits, k=4))}.txt"

    # magic happens here to make it pretty-printed and tournament-compliant
    s = seed.data['spoiler']
    try:
        del s['playthrough']
    except KeyError:
        pass

    try:
        del s['Shops'] #QOL this information is useless for this tournament
    except KeyError:
        pass

    try:
        del s['Bosses'] #QOL this information is useful only for enemizer
    except KeyError:
        pass

    sorteddict = {}

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
    sorteddict['Prizes'] = {}
    for dungeon, prize in prizemap:
        sorteddict['Prizes'][dungeon] = s[dungeon][prize]
    sorteddict['Special']        = s['Special']
    sorteddict['Hyrule Castle']  = sort_dict(s['Hyrule Castle'])
    sorteddict['Eastern Palace'] = sort_dict(s['Eastern Palace'])
    sorteddict['Desert Palace']  = sort_dict(s['Desert Palace'])
    sorteddict['Tower Of Hera']  = sort_dict(s['Tower Of Hera'])
    sorteddict['Castle Tower']   = sort_dict(s['Castle Tower'])
    sorteddict['Dark Palace']    = sort_dict(s['Dark Palace'])
    sorteddict['Swamp Palace']   = sort_dict(s['Swamp Palace'])
    sorteddict['Skull Woods']    = sort_dict(s['Skull Woods'])
    sorteddict['Thieves Town']   = sort_dict(s['Thieves Town'])
    sorteddict['Ice Palace']     = sort_dict(s['Ice Palace'])
    sorteddict['Misery Mire']    = sort_dict(s['Misery Mire'])
    sorteddict['Turtle Rock']    = sort_dict(s['Turtle Rock'])
    sorteddict['Ganons Tower']   = sort_dict(s['Ganons Tower'])
    sorteddict['Light World']    = sort_dict(s['Light World'])
    sorteddict['Death Mountain'] = sort_dict(s['Death Mountain'])
    sorteddict['Dark World']     = sort_dict(s['Dark World'])

    drops = get_seed_prizepacks(seed.data)
    sorteddict['Drops']          = {}
    sorteddict['Drops']['PullTree'] = drops['PullTree']
    sorteddict['Drops']['RupeeCrab'] = {}
    sorteddict['Drops']['RupeeCrab']['Main'] = drops['RupeeCrab']['Main']
    sorteddict['Drops']['RupeeCrab']['Final'] = drops['RupeeCrab']['Final']
    sorteddict['Drops']['Stun'] = drops['Stun']
    sorteddict['Drops']['FishSave'] = drops['FishSave']

    sorteddict['Special']['DiggingGameDigs'] = pyz3r.misc.misc.seek_patch_data(seed.data['patch'], 982421, 1)[0]

    sorteddict['meta']           = s['meta']
    sorteddict['meta']['hash']   = seed.hash
    sorteddict['meta']['permalink'] = seed.url

    for dungeon, prize in prizemap:
        del sorteddict[dungeon][prize]

    async with aiofiles.open(f"{c.SpoilerLogLocal}/{filename}", "w+", newline='\r\n') as out:
        await out.write(json.dumps(sorteddict, indent=4))
        await out.flush()

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

def sort_dict(dict):
    sorteddict = {}
    for key in sorted(dict):
        sorteddict[key] = dict[key]
    return sorteddict