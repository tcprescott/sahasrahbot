# from ..database import alttprgen
import pyz3r
from config import Config as c
# import json
import yaml
import aiofiles
import os

async def get_preset(preset):
    # make sure someone isn't trying some path traversal shennaniganons
    basename = os.path.basename(f'{preset}.yaml')
    try:
        async with aiofiles.open(os.path.join("presets", basename)) as f:
            preset_dict = yaml.load(await f.read(), Loader=yaml.FullLoader)
    except FileNotFoundError:
        return False, False

    seed = await pyz3r.alttpr(
        customizer=preset_dict['customizer'],
        baseurl=c.baseurl,
        seed_baseurl=c.seed_baseurl,
        username=c.username,
        password=c.password,
        settings=preset_dict['settings']
    )
    return seed, preset_dict['goal_name']