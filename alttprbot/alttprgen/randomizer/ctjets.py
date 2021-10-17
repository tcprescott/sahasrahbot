import logging

import aiohttp
from bs4 import BeautifulSoup

jar = aiohttp.CookieJar()


logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)


async def roll_ctjets(**settings):
    # settings = {
    #     'difficulty': 'normal',
    #     'duplicate_char_assignments': '7f7f7f7f7f7f7f',
    #     'shop_prices': 'Normal',
    #     'tech_rando': 'Normal',
    # }

    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        async with session.get(url='http://www.ctjot.com/3_1_0/options/') as resp:
            soup = BeautifulSoup(await resp.text(), features="html5lib")

        csrfmiddlewaretoken = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']

        formdata = aiohttp.FormData()

        formdata.add_field('csrfmiddlewaretoken', csrfmiddlewaretoken)
        formdata.add_field('seed', '')

        for key, val in settings.items():
            formdata.add_field(key, val)

        with open('/opt/data/chronotrigger.sfc', 'rb') as rom:
            formdata.add_field('rom_file', rom.read(), filename=None)

        async with session.post(url='http://www.ctjot.com/3_1_0/generate-rom/', data=formdata) as resp:
            # print(resp.status)
            # print(await resp.text())
            soup = BeautifulSoup(await resp.text(), features="html5lib")

        relative_uri = soup.find('a', text='Seed share link')['href']

        return f"http://ctjets.com{relative_uri}"
