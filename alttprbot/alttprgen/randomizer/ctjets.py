import logging
import os
import aiofiles
import yaml

import aiohttp
from bs4 import BeautifulSoup

from alttprbot.alttprgen.preset import PresetNotFoundException

jar = aiohttp.CookieJar()


logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)


async def fetch_preset(preset):
    preset = preset.lower()

    # make sure someone isn't trying some path traversal shennaniganons
    basename = os.path.basename(f'{preset}.yaml')

    try:
        async with aiofiles.open(os.path.join(f"presets/ctjets", basename)) as f:
            preset_dict = yaml.safe_load(await f.read())
    except FileNotFoundError as err:
        raise PresetNotFoundException(f'Could not find preset {preset}.') from err

    return preset_dict


async def roll_ctjets(settings: dict, version: str = '3_1_0'):
    version = version.replace('.', '_')

    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        async with session.get(url=f'http://www.ctjot.com/{version}/options/') as resp:
            soup = BeautifulSoup(await resp.text(), features="html5lib")

        csrfmiddlewaretoken = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']

        formdata = aiohttp.FormData()

        formdata.add_field('csrfmiddlewaretoken', csrfmiddlewaretoken)
        formdata.add_field('seed', '')

        for key, val in settings.items():
            formdata.add_field(key, val)

        with open('/opt/data/chronotrigger.sfc', 'rb') as rom:
            formdata.add_field('rom_file', rom.read(), filename=None)

        async with session.post(url=f'http://www.ctjot.com/{version}/generate-rom/', data=formdata) as resp:
            soup = BeautifulSoup(await resp.text(), features="html5lib")

        relative_uri = soup.find('a', text='Seed share link')['href']

        return f"http://www.ctjot.com{relative_uri}"
