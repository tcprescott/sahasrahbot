import aiofiles
import aiohttp
from bs4 import BeautifulSoup

from alttprbot.exceptions import SeedGenerationError


async def roll_ctjets(settings: dict, version: str = '3_1_0'):
    version = version.replace('.', '_')
    jar = aiohttp.CookieJar()

    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        async with session.get(url=f'https://ctjot.com/{version}/options/') as resp:
            soup = BeautifulSoup(await resp.text(), features="html5lib")

        csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if csrf_input is None:
            raise SeedGenerationError("Could not find the CSRF token on the ctjot.com options page.")
        csrfmiddlewaretoken = csrf_input['value']

        formdata = aiohttp.FormData()

        formdata.add_field('csrfmiddlewaretoken', csrfmiddlewaretoken)
        formdata.add_field('seed', '')

        for key, val in settings.items():
            formdata.add_field(key, val)

        async with aiofiles.open('/opt/data/chronotrigger.sfc', 'rb') as rom:
            formdata.add_field('rom_file', await rom.read(), filename=None)

        headers = {
            'Referer': f'https://ctjot.com/{version}/options/',
        }

        async with session.post(url=f'https://ctjot.com/{version}/generate-rom/', data=formdata,
                                headers=headers) as resp:
            soup = BeautifulSoup(await resp.text(), features="html5lib")

        share_link = soup.find('a', string='Seed share link')
        if share_link is None:
            raise SeedGenerationError("ctjot.com did not return a seed share link.")

        return f"https://www.ctjot.com{share_link['href']}"
