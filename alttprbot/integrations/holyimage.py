"""The holy image index on alttp.mymm1.com."""
import json

import aiohttp

BASE_URL = 'http://alttp.mymm1.com/holyimage/'
INDEX_URL = BASE_URL + 'holyimages.json'


async def get_holy_images() -> dict:
    """Every holy image, keyed by game slug (``{'z3r': [{'slug': ..., 'idx': ...}, ...], ...}``).

    Parsed from the raw body, so a wrong Content-Type from the host doesn't matter.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(INDEX_URL) as resp:
            text = await resp.read()

    return json.loads(text)
