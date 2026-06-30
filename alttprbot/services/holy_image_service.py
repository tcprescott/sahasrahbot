"""Holy image lookup against the external alttp.mymm1.com catalog.

Fetches the holy-image JSON (cached) and resolves a single image by
slug/alias/idx, raising :class:`HolyImageNotFound` on a miss. The Discord embed
is built in the presentation tier (``presentation/discord/util/holy_image.py``);
this service holds no ``discord`` import.
"""

import json

import aiohttp
from aiocache import Cache, cached

from alttprbot.exceptions import HolyImageNotFound

HOLYIMAGE_JSON_URL = "http://alttp.mymm1.com/holyimage/holyimages.json"


@cached(ttl=300, cache=Cache.MEMORY, key="holyimages")
async def _fetch_all_images() -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(HOLYIMAGE_JSON_URL) as resp:
            text = await resp.read()
    return json.loads(text)


class HolyImageService:
    async def get_all_images(self) -> dict:
        """Return the full holy-image catalog (cached for 5 minutes)."""
        return await _fetch_all_images()

    async def get_image(self, slug, game="z3r"):
        """Resolve a single holy image to ``(image_dict, link)``.

        Raises :class:`HolyImageNotFound` if no slug is given or no image matches
        the slug/alias/idx within the game.
        """
        if slug is None:
            raise HolyImageNotFound(
                "You must specify a holy image.  Check out <http://alttp.mymm1.com/holyimage/>")

        images = await self.get_all_images()
        i = images[game]

        try:
            image = next(item for item in i if item["slug"] == slug.lower() or slug.lower(
            ) in item.get("aliases", []) or slug.lower() == str(item["idx"]))
        except (StopIteration, KeyError) as err:
            raise HolyImageNotFound(
                "That holy image does not exist.  Check out <http://alttp.mymm1.com/holyimage/>") from err

        link = f"http://alttp.mymm1.com/holyimage/{game}-{image['slug']}.html"
        return image, link
