import aiohttp
import os

OOTR_BASE_URL = os.environ.get('OOTR_BASE_URL', 'https://ootrandomizer.com')
OOTR_API_KEY = os.environ.get('OOTR_API_KEY')


async def roll_ootr(settings, version='6.1.0', encrypt=True):
    async with aiohttp.request(
        method='post',
        url=f"{OOTR_BASE_URL}/api/sglive/seed/create",
        raise_for_status=True,
        json=settings,
        params={
            "key": OOTR_API_KEY,
            "version": version,
            "encrypt": str(encrypt).lower()
        }
    ) as resp:
        result = await resp.json()

    return result
