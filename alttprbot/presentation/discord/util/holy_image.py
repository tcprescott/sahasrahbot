"""Discord rendering for holy images.

Builds the holy-image embed from a catalog entry resolved by
:class:`~alttprbot.services.holy_image_service.HolyImageService`. This is the
presentation-tier concern split out of the old ``alttprbot.util.holyimage``
module; the fetch/lookup lives in the service.
"""

from urllib.parse import urljoin

import discord
import html2markdown


def create_holy_image_embed(image: dict, link: str) -> discord.Embed:
    embed = discord.Embed(
        title=image.get('title'),
        description=html2markdown.convert(image['desc']) if 'desc' in image else None,
        color=discord.Colour.from_rgb(0xFF, 0xAF, 0x00)
    )

    if 'url' in image:
        url = urljoin('http://alttp.mymm1.com/holyimage/', image['url'])
        if image.get('mode', '') == 'redirect':
            embed.add_field(name='Link', value=url, inline=False)
        else:
            embed.set_thumbnail(url=url)

    embed.add_field(name="Source", value=link)

    if 'credit' in image:
        embed.set_footer(text=f"Created by {image['credit']}")

    return embed
