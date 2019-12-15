import random
from ..util.alttpr_discord import alttpr
from ..util.http import request_generic
import os
import aiofiles
import yaml
from config import Config as c
import pyz3r

class WeightsetNotFoundException(Exception):
    pass

async def generate_random_game(weightset='weighted', tournament=True, spoilers="off", custom_weightset_url=None):
    basename = os.path.basename(f'{weightset}.yaml')

    if not weightset == 'custom':
        try:
            async with aiofiles.open(os.path.join("weights", basename)) as f:
                weights = yaml.load(await f.read(), Loader=yaml.FullLoader)
        except FileNotFoundError:
            raise WeightsetNotFoundException(f'Could not find weightset {weightset}.  See a list of available weights at <https://l.synack.live/weights>')
    elif weightset == 'custom' and custom_weightset_url:
        weights = await request_generic(custom_weightset_url, method='get', returntype='yaml')


    settings = pyz3r.mystery.generate_random_settings(weights=weights, spoilers=spoilers)

    seed = await alttpr(settings=settings)
    return seed

def get_random_option(optset):
    return random.choices(population=list(optset.keys()),weights=list(optset.values()))[0]