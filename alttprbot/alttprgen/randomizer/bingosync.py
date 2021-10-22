import os
import logging

import aiohttp
from bs4 import BeautifulSoup

from alttprbot.exceptions import SahasrahBotException

BINGOSYNC_BASE_URL = os.environ.get('BINGOSYNC_BASE_URL', 'https://bingosync.com')

jar = aiohttp.CookieJar(unsafe=True)
try:
    jar.load('data/bingosync.cookie')
except FileNotFoundError:
    logging.warning("No bingosync cookie file found.  Will skip loading...")

# WARNING: This is incredibly jank and relies on private endpoints within Bingosync
# that are not intended for public consumption.
# This could break at any time, and it would be our problem, not Bingosync's problem.

class BingoSync(object):
    def __init__(self, nickname="SahasrahBot", base_url=BINGOSYNC_BASE_URL):
        self.base_url = base_url
        self.nickname = nickname
        self.password = None
        self.room_id = None

    @classmethod
    async def generate(cls, nickname="SahasrahBot", base_url=BINGOSYNC_BASE_URL, **kwargs):
        bingo = cls(nickname, base_url)
        await bingo.create_bingo_room(**kwargs)
        return bingo

    @classmethod
    async def retrieve(cls, room_id, password, nickname="SahasrahBot", base_url=BINGOSYNC_BASE_URL):
        bingo = cls(nickname, base_url)
        bingo.room_id = room_id
        bingo.password = password
        return bingo

    async def create_bingo_room(self, room_name, passphrase, game_type, variant_type=None, lockout_mode='1', seed='', custom_json='', is_spectator='on', hide_card='on'):
        csrftoken = await self.get_csrf_token()
        data = {
            'csrfmiddlewaretoken': csrftoken,
            'nickname': self.nickname,
            'room_name': room_name,
            'passphrase': passphrase,
            'game_type': game_type,
            'lockout_mode': lockout_mode,
            'seed': seed,
            'custom_json': custom_json,
            'is_spectator': is_spectator,
            'hide_card': hide_card
        }

        if variant_type is not None:
            data['variant_type'] = variant_type

        async with aiohttp.ClientSession(cookie_jar=jar) as session:
            async with session.request(
                method='post',
                url=BINGOSYNC_BASE_URL,
                headers={'Origin': BINGOSYNC_BASE_URL,
                        'Referer': BINGOSYNC_BASE_URL},
                allow_redirects=False,
                raise_for_status=True,
                data=data
            ) as resp:
                jar.save('data/bingosync.cookie')
                print(await resp.text())
                if resp.status == 302:
                    self.room_id: str = resp.headers['Location'].split("/")[-1]
                    self.password = data['passphrase']
                else:
                    raise SahasrahBotException("Unable to create BingoSync room!")

    # async def join_room(self):
    #     data = {
    #         'room': self.room_id,
    #         'nickname': self.nickname,
    #         'password': self.password
    #     }

    #     async with aiohttp.ClientSession(cookie_jar=jar) as session:
    #         async with session.request(
    #             method='put',
    #             url=f"{BINGOSYNC_BASE_URL}/api/new-card",
    #             raise_for_status=True,
    #             json=data
    #         ) as resp:
    #             resp_data = await resp.json()
    #             self.socket_key = resp_data['socket_key']

    async def new_card(self, game_type, variant_type=None, lockout_mode='1', seed='', custom_json='', hide_card='on'):
        data = {
            'hide_card': hide_card == 'on',
            'game_type': game_type,
            'custom_json': custom_json,
            'lockout_mode': lockout_mode,
            'seed': seed,
            'room': self.room_id
        }

        if variant_type is not None:
            data['variant_type'] = variant_type

        async with aiohttp.ClientSession(cookie_jar=jar) as session:
            async with session.request(
                method='put',
                url=f"{BINGOSYNC_BASE_URL}/api/new-card",
                raise_for_status=True,
                json=data
            ) as resp:
                return await resp.text()

    @property
    def url(self):
        return f"{self.base_url}/room/{self.room_id}"

    async def get_csrf_token(self):
        async with aiohttp.ClientSession(cookie_jar=jar) as session:
            try:
                async with session.request(
                    method='get',
                    url=self.base_url,
                    raise_for_status=True
                ) as resp:
                    soup = BeautifulSoup(await resp.text(), features="html5lib")
            except Exception as e:
                raise SahasrahBotException("Unable to acquire CSRF token.  Please contact Synack for help.") from e

            return soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
