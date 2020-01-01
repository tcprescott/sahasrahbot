import json

import aiohttp

async def holy(slug, game='z3r'):
    image = HolyImage(slug=slug, game=game)
    await image._init()
    return image

class HolyImageNotFound(Exception):
    pass

class HolyImage():
    def __init__(self, slug, game='z3r'):
        self.slug = slug
        self.game = game

    async def _init(self):
        if self.slug is None:
            raise HolyImageNotFound('You must specify a holy image.  Check out <http://alttp.mymm1.com/holyimage/>')

        images = await get_json('http://alttp.mymm1.com/holyimage/holyimages.json')
        i = images[self.game]

        try:
            image = next(item for item in i if item["slug"] == self.slug or self.slug in item.get("aliases", []) or self.slug == str(item["idx"]))
        except StopIteration:
            raise HolyImageNotFound('That holy image does not exist.  Check out <http://alttp.mymm1.com/holyimage/>')

        self.image = image
        self.link = f"http://alttp.mymm1.com/holyimage/{self.game}-{self.image['slug']}.html"

async def get_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.read()

    return json.loads(text)
