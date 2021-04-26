import json
from urllib.parse import urljoin

import aiohttp
import discord
import html2markdown

from alttprbot.exceptions import SahasrahBotException


async def holy(slug, game='z3r'):
    image = HolyImage(slug=slug, game=game)
    await image._init()
    return image


class HolyImageNotFound(SahasrahBotException):
    pass


class HolyImage():
    def __init__(self, slug, game='z3r'):
        self.slug = slug
        self.game = game

    async def _init(self):
        if self.slug is None:
            raise HolyImageNotFound(
                'You must specify a holy image.  Check out <http://alttp.mymm1.com/holyimage/>')

        images = await get_json('http://alttp.mymm1.com/holyimage/holyimages.json')
        i = images[self.game]

        try:
            image = next(item for item in i if item["slug"] == self.slug.lower() or self.slug.lower(
            ) in item.get("aliases", []) or self.slug.lower() == str(item["idx"]))
        except (StopIteration, KeyError) as err:
            raise HolyImageNotFound(
                'That holy image does not exist.  Check out <http://alttp.mymm1.com/holyimage/>') from err

        self.image = image
        self.link = f"http://alttp.mymm1.com/holyimage/{self.game}-{self.image['slug']}.html"

    @classmethod
    async def construct(cls, slug, game):
        image = cls(slug=slug, game=game)
        await image._init()
        return image

    @property
    def embed(self):
        embed = discord.Embed(
            title=self.image.get('title'),
            description=html2markdown.convert(self.image['desc']) if 'desc' in self.image else None,
            color=discord.Colour.from_rgb(0xFF, 0xAF, 0x00)
        )

        if 'url' in self.image:
            url = urljoin('http://alttp.mymm1.com/holyimage/', self.image['url'])
            if self.image.get('mode', '') == 'redirect':
                embed.add_field(name='Link', value=url, inline=False)
            else:
                embed.set_thumbnail(url=url)

        embed.add_field(name="Source", value=self.link)

        if 'credit' in self.image:
            embed.set_footer(text=f"Created by {self.image['credit']}")

        return embed


async def get_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.read()

    return json.loads(text)
