"""The holy image index on alttp.mymm1.com."""
import json

import aiohttp

# alttp.mymm1.com serves no HTTPS (the TLS handshake fails), so plain HTTP it is.
BASE_URL = 'http://alttp.mymm1.com/holyimage/'  # NOSONAR
INDEX_URL = BASE_URL + 'holyimages.json'


async def get_holy_images() -> dict:
    """Every holy image, keyed by game slug (``{'z3r': [{'slug': ..., 'idx': ...}, ...], ...}``).

    Parsed from the raw body, so a wrong Content-Type from the host doesn't matter.
    """
    async with aiohttp.ClientSession() as session, session.get(INDEX_URL) as resp:
        text = await resp.read()

    return json.loads(text)
