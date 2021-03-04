import gzip
import json
import random
import string
import os

import aioboto3

# from config import Config as c

from .preset import fetch_preset, generate_preset
from .ext.progression_spoiler import create_progression_spoiler


async def generate_spoiler_game(preset, spoiler_type='spoiler'):
    preset_dict = await fetch_preset(preset, 'alttpr')
    seed = await generate_preset(preset_dict, preset=preset, spoilers="generate", tournament=True, allow_quickswap=True)
    if not seed:
        return False, False, False
    spoiler_log_url = await write_json_to_disk(seed, spoiler_type)
    return seed, preset_dict, spoiler_log_url


async def generate_spoiler_game_custom(preset_dict, spoiler_type='spoiler'):
    seed = await generate_preset(preset_dict, preset="custom", spoilers="generate", tournament=True, allow_quickswap=True)
    if not seed:
        return False, False, False
    spoiler_log_url = await write_json_to_disk(seed, spoiler_type)
    return seed, preset_dict, spoiler_log_url


async def write_json_to_disk(seed, spoiler_type='spoiler'):
    filename = f"{spoiler_type}__{seed.hash}__{'-'.join(seed.code).replace(' ', '')}__{''.join(random.choices(string.ascii_letters + string.digits, k=4))}.txt"

    if spoiler_type == 'progression':
        sorteddict = create_progression_spoiler(seed)
    else:
        sorteddict = seed.get_formatted_spoiler(translate_dungeon_items=True)

    payload = gzip.compress(json.dumps(sorteddict, indent=4).encode('utf-8'))

    async with aioboto3.client('s3') as s3:
        await s3.put_object(
            Bucket=os.environ.get('AWS_SPOILER_BUCKET_NAME'),
            Key=filename,
            Body=payload,
            ACL='public-read',
            ContentEncoding='gzip',
            ContentDisposition='attachment'
        )

    return f"{os.environ.get('SpoilerLogUrlBase')}/{filename}"
