import ssl

import aiohttp
from racetime_bot import Bot
from tenacity import (AsyncRetrying, RetryError, retry_if_exception_type,
                      stop_after_attempt)

import config
from alttprbot.services import racetime_rooms

RACETIME_HOST = config.RACETIME_HOST
RACETIME_SECURE = config.RACETIME_SECURE
RACETIME_PORT = config.RACETIME_PORT


class SahasrahBotRaceTimeBot(Bot):
    racetime_host = RACETIME_HOST
    racetime_port = RACETIME_PORT
    racetime_secure = RACETIME_SECURE

    def __init__(self, handler_class, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handler_class = handler_class
        if self.racetime_secure:
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

    def get_handler_kwargs(self, ws_conn, state):
        return {
            'conn': ws_conn,
            'logger': self.logger,
            'state': state,
            'command_prefix': config.RACETIME_COMMAND_PREFIX,
        }

    def get_handler_class(self):
        return self.handler_class

    async def start(self):
        self.http = aiohttp.ClientSession(raise_for_status=True)
        if not await self._authorize():
            return
        self.loop.create_task(self.reauthorize())
        self.loop.create_task(self.refresh_races())

        unlisted_rooms = await racetime_rooms.unlisted_rooms(self.category_slug)
        for unlisted_room in unlisted_rooms:
            try:
                await self._resume_unlisted_room(unlisted_room.room_name)
            except RetryError as e:
                if e.last_attempt and e.last_attempt._exception:
                    raise e.last_attempt._exception from e
                else:
                    raise RuntimeError("RetryError occurred but no exception found in last_attempt.") from e

    async def _authorize(self) -> bool:
        """Get an access token; False (after logging why) when racetime.gg refused."""
        try:
            result = await self.authorize()
        except aiohttp.ClientResponseError as e:
            if e.status == 401:
                self.logger.error(f'RaceTime API returned 401 Unauthorized while attempting to create bot for {self.category_slug}. '
                                  f'Please check your API key and try again.')
                return False
            raise
        if result is None:
            self.logger.error('Authorization failed: authorize() returned None.')
            return False
        self.access_token, self.reauthorize_every = result
        return True

    async def _resume_unlisted_room(self, room_name: str):
        """Rejoin an unlisted room we opened, or forget it once it's over or listed."""
        race_data = None
        async for attempt in AsyncRetrying(
                stop=stop_after_attempt(5),
                retry=retry_if_exception_type(aiohttp.ClientResponseError)):
            with attempt:
                async with self.http.get(
                        self.http_uri(f'/{room_name}/data'),
                        ssl=self.ssl_context,
                ) as resp:
                    race_data = await resp.json()

        if race_data and (race_data['status']['value'] in ['finished', 'cancelled'] or not race_data['unlisted']):
            await racetime_rooms.forget_unlisted(room_name)
        elif race_data:
            await self.join_race_room(room_name)
