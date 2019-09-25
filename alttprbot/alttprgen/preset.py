# from ..database import alttprgen
import pyz3r
from config import Config as c
# import json
import yaml
import aiofiles
import os

async def get_preset(preset, hints=False, spoilers_ongen=False):
    # make sure someone isn't trying some path traversal shennaniganons
    basename = os.path.basename(f'{preset}.yaml')
    try:
        async with aiofiles.open(os.path.join("presets", basename)) as f:
            preset_dict = yaml.load(await f.read(), Loader=yaml.FullLoader)
    except FileNotFoundError:
        return False, False

    if not preset_dict['customizer']:
        if hints:
            preset_dict['settings']['hints'] = 'on'
        else:
            preset_dict['settings']['hints'] = 'off'

    if spoilers_ongen:
        preset_dict['settings']['tournament'] = True
        preset_dict['settings']['spoilers_ongen'] = True
        preset_dict['settings']['spoilers'] = False
    else:
        preset_dict['settings']['tournament'] = True
        preset_dict['settings']['spoilers_ongen'] = False
        preset_dict['settings']['spoilers'] = False

    seed = await pyz3r.alttpr(
        customizer=preset_dict['customizer'],
        baseurl=c.baseurl,
        seed_baseurl=c.seed_baseurl,
        username=c.username,
        password=c.password,
        settings=preset_dict['settings']
    )
    return seed, preset_dict['goal_name']