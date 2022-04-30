import aiohttp
from bs4 import BeautifulSoup

jar = aiohttp.CookieJar()


async def roll_ctjets(settings: dict, version: str = '3_1_0'):
    version = version.replace('.', '_')

    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        async with session.get(url=f'https://ctjot.com/{version}/options/') as resp:
            soup = BeautifulSoup(await resp.text(), features="html5lib")

        csrfmiddlewaretoken = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']

        formdata = aiohttp.FormData()

        formdata.add_field('csrfmiddlewaretoken', csrfmiddlewaretoken)
        formdata.add_field('seed', '')

        for key, val in settings.items():
            formdata.add_field(key, val)

        with open('/opt/data/chronotrigger.sfc', 'rb') as rom:
            formdata.add_field('rom_file', rom.read(), filename=None)

        headers = {
            'Referer': f'https://ctjot.com/{version}/options/',
        }

        async with session.post(url=f'https://ctjot.com/{version}/generate-rom/', data=formdata, headers=headers) as resp:
            soup = BeautifulSoup(await resp.text(), features="html5lib")

        relative_uri = soup.find('a', text='Seed share link')['href']

        return f"http://www.ctjot.com{relative_uri}"
