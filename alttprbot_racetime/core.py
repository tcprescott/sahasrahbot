import asyncio
import json
import ssl
from functools import partial

import aiohttp
from racetime_bot import Bot
from tenacity import (AsyncRetrying, RetryError, retry_if_exception_type,
                      stop_after_attempt, wait_exponential)

import config
from alttprbot import models
from alttprbot_racetime.compat import HandlerTask, get_room_handler

RACETIME_HOST = config.RACETIME_HOST
RACETIME_SECURE = config.RACETIME_SECURE
RACETIME_PORT = config.RACETIME_PORT


class SahasrahBotRaceTimeBot(Bot):
    racetime_host = RACETIME_HOST
    racetime_port = RACETIME_PORT
    racetime_secure = RACETIME_SECURE

    def __init__(self, handler_class, category_slug, client_id, client_secret, logger, ssl_context=None):
        self.logger = logger
        self.category_slug = category_slug
        self.ssl_context = ssl_context

        self.last_scan = None
        self.handlers = {}
        self.races = {}
        self.state = {}

        self.client_id = client_id
        self.client_secret = client_secret

        self.access_token = None
        self.http = None
        self.join_lock = asyncio.Lock()
        self.reauthorize_every = 36000
        self._background_tasks = set()
        self._stopping = False

        self.handler_class = handler_class
        if self.racetime_secure:
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

    def _create_background_task(self, coro):
        if self._stopping:
            coro.close()
            return None

        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    def get_handler_kwargs(self, ws_conn, state):
        return {
            'conn': ws_conn,
            'logger': self.logger,
            'state': state,
            'command_prefix': config.RACETIME_COMMAND_PREFIX,
            'bot': self,
        }

    def get_handler_class(self):
        return self.handler_class

    def uri(self, proto, url, port=None):
        if port:
            return '%(proto)s://%(host)s:%(port)s%(url)s' % {
                'proto': proto,
                'host': self.racetime_host,
                'url': url,
                'port': port,
            }

        return '%(proto)s://%(host)s%(url)s' % {
            'proto': proto,
            'host': self.racetime_host,
            'url': url,
        }

    def http_uri(self, url):
        return self.uri(
            proto='https' if self.racetime_secure else 'http',
            url=url,
            port=self.racetime_port,
        )

    def ws_uri(self, url):
        return self.uri(
            proto='wss' if self.racetime_secure else 'ws',
            url=url,
            port=self.racetime_port,
        )

    async def authorize(self):
        try:
            async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(5),
                    retry=retry_if_exception_type(aiohttp.ClientResponseError),
                    wait=wait_exponential(multiplier=1, min=4, max=10)):
                with attempt:
                    async with self.http.post(self.http_uri('/o/token'), data={
                        'client_id': self.client_id,
                        'client_secret': self.client_secret,
                        'grant_type': 'client_credentials',
                    }, ssl=self.ssl_context if self.ssl_context is not None else self.racetime_secure) as resp:
                        data = await resp.json()
                        if not data.get('access_token'):
                            raise Exception('Unable to retrieve access token.')
                        return data.get('access_token'), data.get('expires_in', 36000)
        except RetryError as e:
            if e.last_attempt and e.last_attempt.exception():
                raise e.last_attempt.exception() from e
            raise RuntimeError("RetryError occurred but no exception found in last_attempt.") from e

    async def create_handler(self, race_data):
        ws_conn = await self.http.ws_connect(
            self.ws_uri(race_data.get('websocket_bot_url')),
            headers={
                'Authorization': 'Bearer ' + self.access_token,
            },
            ssl=self.ssl_context if self.ssl_context is not None else self.racetime_secure,
        )

        race_name = race_data.get('name')
        if race_name not in self.state:
            self.state[race_name] = {}

        cls = self.get_handler_class()
        kwargs = self.get_handler_kwargs(ws_conn, self.state[race_name])

        handler = cls(**kwargs)
        handler.data = race_data

        self.logger.info(
            'Created handler for %(race)s'
            % {'race': race_data.get('name')}
        )

        return handler

    async def reauthorize(self):
        try:
            while not self._stopping:
                self.logger.info('Get new access token')
                self.access_token, self.reauthorize_every = await self.authorize()

                for name in list(self.handlers):
                    room_handler = get_room_handler(self, name)
                    if room_handler is None or getattr(room_handler, 'ws', None) is None:
                        continue
                    try:
                        await asyncio.wait_for(room_handler.ws.close(), timeout=30)
                    except asyncio.TimeoutError:
                        self.logger.exception("Timed out waiting for websocket to close to allow for reconnection.")

                delay = self.reauthorize_every
                if delay > 600:
                    delay -= 600
                await asyncio.sleep(delay)
        except asyncio.CancelledError:
            self.logger.info('Reauthorize loop cancelled for %s.', self.category_slug)
            raise

    def _track_handler_task(self, race_name, handler):
        def done(task_name, task):
            if task_name in self.handlers:
                del self.handlers[task_name]

            if task.cancelled() or self._stopping:
                return

            exception = task.exception()
            if exception is not None:
                self.logger.error(
                    "Handler task crashed for %s in %s.",
                    task_name,
                    self.category_slug,
                    exc_info=(type(exception), exception, exception.__traceback__),
                )

        task = asyncio.create_task(handler.handle())
        task.add_done_callback(partial(done, race_name))
        self.handlers[race_name] = HandlerTask(task=task, handler=handler)

    async def get_data(self):
        async with self.http.get(
                self.http_uri(f'/{self.category_slug}/data'),
                ssl=self.ssl_context,
        ) as resp:
            return await resp.json()

    async def get_team(self, team_name):
        try:
            async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(5),
                    retry=retry_if_exception_type(aiohttp.ClientResponseError),
                    wait=wait_exponential(multiplier=1, min=4, max=10)):
                with attempt:
                    async with self.http.get(
                            self.http_uri(f'/team/{team_name}/data'),
                            ssl=self.ssl_context,
                    ) as resp:
                        return await resp.json()
        except RetryError as e:
            if e.last_attempt and e.last_attempt.exception():
                raise e.last_attempt.exception() from e
            raise RuntimeError("RetryError occurred but no exception found in last_attempt.") from e

    async def refresh_races(self):
        try:
            while not self._stopping:
                self.logger.debug('Refresh races')
                try:
                    data = await self.get_data()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    if self._stopping:
                        break
                    self.logger.error('Fatal error when attempting to retrieve race data.', exc_info=True)
                    await asyncio.sleep(self.scan_races_every)
                    continue

                self.races = {}
                for race in data.get('current_races', []):
                    self.races[race.get('name')] = race

                for name, summary_data in self.races.items():
                    async with self.join_lock:
                        if name in self.handlers:
                            continue
                        try:
                            async with self.http.get(
                                    self.http_uri(summary_data.get('data_url')),
                                    ssl=self.ssl_context,
                            ) as resp:
                                race_data = await resp.json()
                        except asyncio.CancelledError:
                            raise
                        except Exception:
                            if self._stopping:
                                break
                            self.logger.error('Fatal error when attempting to retrieve summary data.', exc_info=True)
                            await asyncio.sleep(self.scan_races_every)
                            continue

                        if self.should_handle(race_data):
                            try:
                                handler = await self.create_handler(race_data)
                            except Exception:
                                self.logger.exception("Failed to create handler.")
                                continue
                            self._track_handler_task(name, handler)
                        else:
                            if name in self.state:
                                del self.state[name]
                            self.logger.info(
                                'Ignoring %(race)s by configuration.'
                                % {'race': race_data.get('name')}
                            )

                await asyncio.sleep(self.scan_races_every)
        except asyncio.CancelledError:
            self.logger.info('Refresh loop cancelled for %s.', self.category_slug)
            raise

    async def join_race_room(self, race_name, force=False):
        self.logger.info(f'Attempting to join {race_name}')

        if not race_name.split('/')[0] == self.category_slug:
            raise Exception('Race is not for the bot\'s category category.')

        try:
            async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(5),
                    retry=retry_if_exception_type(aiohttp.ClientResponseError),
                    wait=wait_exponential(multiplier=1, min=4, max=10)):
                with attempt:
                    async with self.http.get(
                            self.http_uri(f'/{race_name}/data'),
                            ssl=self.ssl_context,
                    ) as resp:
                        data = await resp.json()
        except RetryError as e:
            raise e.last_attempt._exception from e

        name = data['name']

        async with self.join_lock:
            if name in self.handlers:
                self.logger.info(f'Returning existing handler for {name}')
                return get_room_handler(self, name)

            if self.should_handle(data) or force:
                handler = await self.create_handler(data)
                self._track_handler_task(name, handler)
                return handler

            if name in self.state:
                del self.state[name]
            self.logger.info(
                'Ignoring %(race)s by configuration.'
                % {'race': data.get('name')}
            )

        return None

    async def startrace(self, **kwargs):
        if kwargs.get('goal') and kwargs.get('custom_goal'):
            raise Exception('Either a goal or custom_goal can be specified, but not both.')

        data = await self.get_data()
        goals = data.get('goals', [])

        if kwargs.get('goal') not in goals:
            self.logger.error(f'Invalid goal: {kwargs.get("goal")}.  We will instead use a custom goal.')
            kwargs['custom_goal'] = kwargs.get('goal')
            kwargs.pop('goal', None)

        try:
            async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(5),
                    retry=retry_if_exception_type(aiohttp.ClientResponseError),
                    wait=wait_exponential(multiplier=1, min=4, max=10)):
                with attempt:
                    async with self.http.post(
                            url=self.http_uri(f'/o/{self.category_slug}/startrace'),
                            data=kwargs,
                            ssl=self.ssl_context,
                            headers={
                                'Authorization': 'Bearer ' + self.access_token,
                            }
                    ) as resp:
                        headers = resp.headers
        except RetryError as e:
            raise e.last_attempt._exception from e

        if 'Location' in headers:
            race_name = headers['Location'][1:]
            return await self.join_race_room(race_name)

        raise Exception('Received an unexpected response when creating a race.')

    async def start(self):
        self.http = aiohttp.ClientSession(raise_for_status=True)
        try:
            result = await self.authorize()
            if result is None:
                self.logger.error('Authorization failed: authorize() returned None.')
                await self.http.close()
                return
            self.access_token, self.reauthorize_every = result

            if self._stopping:
                if not self.http.closed:
                    await self.http.close()
                return

        except aiohttp.ClientResponseError as e:
            if e.status == 401:
                self.logger.error(f'RaceTime API returned 401 Unauthorized while attempting to create bot for {self.category_slug}. '
                                 f'Please check your API key and try again.')
                await self.http.close()
                return
            else:
                await self.http.close()
                raise
        except asyncio.CancelledError:
            await self.stop()
            raise
        except Exception:
            if self.http is not None and not self.http.closed:
                await self.http.close()
            raise
        self._create_background_task(self.reauthorize())
        self._create_background_task(self.refresh_races())

        unlisted_rooms = await models.RTGGUnlistedRooms.filter(category=self.category_slug)
        for unlisted_room in unlisted_rooms:
            try:
                race_data = None
                async for attempt in AsyncRetrying(
                        stop=stop_after_attempt(5),
                        retry=retry_if_exception_type(aiohttp.ClientResponseError)):
                    with attempt:
                        async with self.http.get(
                                self.http_uri(f'/{unlisted_room.room_name}/data'),
                                ssl=self.ssl_context,
                        ) as resp:
                            race_data = await resp.json()

                if race_data and (race_data['status']['value'] in ['finished', 'cancelled'] or not race_data['unlisted']):
                    await unlisted_room.delete()
                elif race_data:
                    await self.join_race_room(unlisted_room.room_name)

            except RetryError as e:
                if e.last_attempt and e.last_attempt._exception:
                    raise e.last_attempt._exception from e
                else:
                    raise RuntimeError("RetryError occurred but no exception found in last_attempt.") from e
            except asyncio.CancelledError:
                await self.stop()
                raise

    async def stop(self):
        if self._stopping:
            return

        self._stopping = True

        handler_tasks = []
        for entry in list(self.handlers.values()):
            handler = getattr(entry, 'handler', entry)
            ws = getattr(handler, 'ws', None)
            if ws is not None and not ws.closed:
                try:
                    await ws.close()
                except Exception:
                    self.logger.debug('Failed to close websocket cleanly during shutdown.', exc_info=True)

            task = getattr(entry, 'task', None)
            if task is not None and not task.done():
                task.cancel()
                handler_tasks.append(task)

        background_tasks = [task for task in self._background_tasks if not task.done()]
        for task in background_tasks:
            task.cancel()

        if handler_tasks or background_tasks:
            await asyncio.gather(*handler_tasks, *background_tasks, return_exceptions=True)

        self.handlers.clear()

        if self.http is not None and not self.http.closed:
            await self.http.close()
