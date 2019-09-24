from ..database import alttprgen
import pyz3r
from config import Config as c
import json

async def get_preset(preset):
    result = await alttprgen.get_seed_preset(preset)
    if not len(result):
        raise Exception('Preset not found.')

    seed = await pyz3r.alttpr(
        customizer=True if result['customizer'] == 1 else False,
        baseurl=c.baseurl,
        seed_baseurl=c.seed_baseurl,
        username=c.username,
        password=c.password,
        settings=json.loads(result['settings'])
    )
    return seed