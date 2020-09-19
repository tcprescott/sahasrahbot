import gzip
import json
import random
import string

import aioboto3
import os

# from config import Config as c

from .preset import get_preset


async def generate_spoiler_game(preset):
    seed, preset_dict = await get_preset(preset, hints=False, spoilers="generate", allow_quickswap=True)
    if not seed:
        return False, False, False
    spoiler_log_url = await write_json_to_disk(seed)
    return seed, preset_dict, spoiler_log_url


async def write_json_to_disk(seed):
    filename = f"spoiler__{seed.hash}__{'-'.join(seed.code).replace(' ', '')}__{''.join(random.choices(string.ascii_letters + string.digits, k=4))}.txt"

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
