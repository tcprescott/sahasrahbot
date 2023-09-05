from dataclasses import dataclass
import gzip
import json
import random
import string
import os

import aioboto3

# from config import Config as c

from alttprbot.alttprgen.generator import ALTTPRPreset, PresetData
from alttprbot_discord.util.alttpr_discord import ALTTPRDiscord
from alttprbot.alttprgen.ext.progression_spoiler import create_progression_spoiler


@dataclass
class ALTTPRSpoilerGame:
    preset: PresetData
    spoiler_log_url: str
    seed: ALTTPRDiscord

async def generate_spoiler_game(preset, spoiler_type='spoiler', festive=False, branch=None, allow_quickswap=True):
    preset_data = ALTTPRPreset(preset)
    await preset_data.fetch()
    seed = await preset_data.generate(
        spoilers="generate",
        tournament=True,
        allow_quickswap=allow_quickswap,
        endpoint_prefix="/festive" if festive else "",
        branch=branch
    )

    spoiler_log_url = await write_json_to_disk(seed, spoiler_type)

    return ALTTPRSpoilerGame(
        preset=preset_data,
        spoiler_log_url=spoiler_log_url,
        seed=seed
    )


async def generate_spoiler_game_custom(content, spoiler_type='spoiler', branch=None):
    preset_data = await ALTTPRPreset.custom(content)
    seed = await preset_data.generate(spoilers="generate", tournament=True, allow_quickswap=True, branch=branch)

    spoiler_log_url = await write_json_to_disk(seed, spoiler_type)

    return ALTTPRSpoilerGame(
        preset=preset_data,
        spoiler_log_url=spoiler_log_url,
        seed=seed
    )


async def write_json_to_disk(seed, spoiler_type='spoiler'):
    filename = f"{spoiler_type}__{seed.hash}__{'-'.join(seed.code).replace(' ', '')}__{''.join(random.choices(string.ascii_letters + string.digits, k=4))}.txt"

    if spoiler_type == 'progression':
        sorteddict = create_progression_spoiler(seed)
    else:
        sorteddict = seed.get_formatted_spoiler(translate_dungeon_items=True)

    payload = gzip.compress(json.dumps(sorteddict, indent=4).encode('utf-8'))

    session = aioboto3.Session()
    async with session.client('s3') as s3:
        await s3.put_object(
            Bucket=os.environ.get('AWS_SPOILER_BUCKET_NAME'),
            Key=filename,
            Body=payload,
            ACL='public-read',
            ContentEncoding='gzip',
            ContentDisposition='attachment'
        )

    return f"{os.environ.get('SpoilerLogUrlBase')}/{filename}"
