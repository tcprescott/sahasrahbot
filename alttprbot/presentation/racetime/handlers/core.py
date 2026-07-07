import asyncio
import json
import math
from datetime import datetime
from itertools import groupby

import aiohttp
import discord.utils
import isodate
from racetime_bot import RaceHandler, can_monitor, monitor_cmd
from tenacity import (AsyncRetrying, RetryError, retry_if_exception_type,
                      stop_after_attempt, wait_exponential)

from alttprbot.exceptions import KONOTSegmentNotFound
from alttprbot.services import (
    AuthorizationService,
    RaceRoomService,
    SpoilerRaceService,
    TournamentResultsService,
)
from alttprbot.presentation.discord.bot import discordbot
from alttprbot.presentation.discord.tournament import dispatch as tournament_dispatch
from alttprbot.presentation.racetime.misc.konot import KONOT
from alttprbot.presentation.racetime.util.arg_parser import arg_parser
from alttprbot.presentation.racetime.util.authz import subject_from_message


class SahasrahBotCoreHandler(RaceHandler):
    """
    SahasrahBot race handler. Generates seeds, presets, and frustration.
    """
    stop_at = ['cancelled', 'finished']
    tournament = None
    konot: KONOT = None
    status = None
    unlisted = False
    spoiler_race = None

    def __init__(self, bot=None, **kwargs):
        self.bot = bot
        # Upstream racetime-bot 2.3.0 ``RaceHandler.__init__`` is
        # ``(logger, conn, state, command_prefix)`` and does not accept a
        # ``bot`` argument (the fork did). Keep our own reference above and
        # forward only the SDK kwargs to the base handler.
        super().__init__(**kwargs)
        self.seed_rolled = False

    async def handle(self):
        """
        Low-level websocket handler loop.

        Mirrors upstream ``RaceHandler.handle`` (``websockets`` transport) but
        dispatches each incoming message to its own task so that a long-running
        command (e.g. seed generation during ``!newrace``) does not block the
        receive loop. This preserves the concurrent-consume behavior the
        previously-used fork provided.
        """
        self.logger.info('[%(race)s] Handler started' % {
            'race': self.data.get('name'),
        })
        async with self.conn as ws:
            self.ws = ws
            if await self.should_stop():
                return
            await self.begin()
            async for message in self.ws:
                data = json.loads(message)
                asyncio.create_task(self.consume(data))
                if await self.should_stop():
                    await self.end()
                    break

    async def chat_message(self, data):
        """
        Consume an incoming ``chat.message`` message and dispatch commands.

        Ported from the previously-used fork so that both ``ex_<cmd>(args,
        message)`` and ``ex2_<cmd>(message, positional_args, keyword_args)``
        command forms are supported (upstream 2.3.0 only dispatches ``ex_*``
        and lowercases the whole message). Case is preserved here so command
        arguments (preset names, branches, seed codes) are passed through
        untouched, and exceptions are echoed back to the race chat.
        """
        message = data.get('message', {})

        if message.get('is_bot') or message.get('is_system'):
            self.logger.debug('Ignoring bot/system message.')
            return

        words = message.get('message', '').split(' ')
        if words and words[0].startswith(self.command_prefix):
            # look to see if there's a command handler for this
            method = 'ex_' + words[0][len(self.command_prefix):]
            if hasattr(self, method):
                args = words[1:]
                self.logger.debug('[%(race)s] Calling handler for %(word)s' % {
                    'race': self.data.get('name'),
                    'word': words[0],
                })
                try:
                    await getattr(self, method)(args, message)
                except Exception as e:
                    self.logger.error('Command raised exception.', exc_info=True)
                    await self.send_message(f'Command raised exception: {str(e)}')

            # if not, look to see if there's a new command handler for this
            method = 'ex2_' + words[0][len(self.command_prefix):]
            if hasattr(self, method):
                self.logger.debug('[%(race)s] Calling new handler for %(word)s' % {
                    'race': self.data.get('name'),
                    'word': words[0],
                })
                try:
                    positional_args, keyword_args = arg_parser(message.get('message', ''))
                    await getattr(self, method)(message, positional_args, keyword_args)
                except Exception as e:
                    self.logger.error('Command raised exception.', exc_info=True)
                    await self.send_message(f'Command raised exception: {str(e)}')

    async def begin(self):
        self.state['locked'] = False

        if self.data.get('status', {}).get('value') in ['open', 'invitational']:
            await self.intro()

        await self.setup_tournament()
        await self.setup_konot()
        await self.setup_spoiler_race()

    async def setup_spoiler_race(self):
        self.spoiler_race = await SpoilerRaceService().get_for_room(self.data.get('name'))

        if self.spoiler_race is None:
            return
        if self.spoiler_race.started is None:
            return

        started_time = self.spoiler_race.started
        now_time = discord.utils.utcnow()
        remaining_duration = (started_time - now_time).total_seconds() + self.spoiler_race.studytime

        if remaining_duration <= 0:
            return

        loop = asyncio.get_running_loop()
        loop.create_task(self.countdown_timer(
            duration_in_seconds=remaining_duration,
            beginmessage=True,
        ))

    async def send_spoiler_log(self):
        if self.spoiler_race is None:
            return

        await SpoilerRaceService().mark_started(self.spoiler_race)
        await self.send_message('Sending spoiler log...')
        await self.send_message('---------------')
        await self.send_message(f"This race\'s spoiler log: {self.spoiler_race.spoiler_url}")
        await self.send_message('---------------')
        await self.send_message('GLHF! :mudora:')
        loop = asyncio.get_running_loop()
        loop.create_task(self.countdown_timer(
            duration_in_seconds=self.spoiler_race.studytime,
            beginmessage=True,
        ))

    async def countdown_timer(self, duration_in_seconds, beginmessage=False):
        loop = asyncio.get_running_loop()

        reminders = [1800, 1500, 1200, 900, 600, 300,
                     120, 60, 30, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
        start_time = loop.time()
        end_time = loop.time() + duration_in_seconds
        while True:
            # logging.info(datetime.datetime.now())
            timeleft = math.ceil(
                start_time - loop.time() + duration_in_seconds)
            # logging.info(timeleft)
            if timeleft in reminders:
                minutes = math.floor(timeleft / 60)
                seconds = math.ceil(timeleft % 60)
                if minutes == 0 and seconds > 10:
                    msg = f'{seconds} second(s) remain!'
                elif minutes == 0 and seconds <= 10:
                    msg = f"{seconds} second(s) remain!"
                else:
                    msg = f'{minutes} minute(s), {seconds} seconds remain!'
                await self.send_message(msg)
                reminders.remove(timeleft)
            if loop.time() >= end_time:
                if beginmessage:
                    await self.send_message('Log study has finished.  Begin racing!')
                break
            await asyncio.sleep(.1 if timeleft <= 10 else 1)

    async def schedule_spoiler_race(self, spoiler_url: str, studytime: int):
        self.spoiler_race = await SpoilerRaceService().schedule(
            srl_id=self.data.get('name'),
            spoiler_url=spoiler_url,
            studytime=studytime,
        )
        return self.spoiler_race

    async def delete_spoiler_race(self):
        if self.spoiler_race:
            await SpoilerRaceService().delete(self.spoiler_race)
        self.spoiler_race = None

    async def setup_tournament(self):
        if self.tournament:
            return

        race = await TournamentResultsService().get_by_srl_id(self.data.get('name'))
        if not race:
            return

        try:
            self.tournament = await tournament_dispatch.fetch_tournament_handler(
                event=race.event,
                episodeid=race.episode_id,
                rtgg_handler=self
            )
            await self.tournament.on_room_resume()
        except Exception:
            self.logger.exception("Error while association tournament race to handler.")

    async def setup_konot(self):
        if self.konot:
            return

        try:
            self.konot = await KONOT.resume(self)
        except KONOTSegmentNotFound:
            self.konot = None

    async def race_data(self, data):
        self.data = data.get('race')

        await self.race_data_hook()

        if self.tournament:
            pending_entrants = [e for e in self.data['entrants'] if e.get('status', {}).get('value', {}) == 'requested']
            for entrant in pending_entrants:
                entrant_id = entrant['user']['id']

                if entrant_id in self.tournament.player_racetime_ids:
                    await self.accept_request(entrant_id)

                elif await self.tournament.can_gatekeep(entrant_id):
                    await self.accept_request(entrant_id)
                    await self.add_monitor(entrant_id)

        fire_event = False

        status = self.data.get('status', {}).get('value')
        if status != self.status and self.status is not None:
            fire_event = True

        self.status = status
        if fire_event:
            self.status = status
            method = f'status_{status}'

            discordbot.dispatch(f"racetime_{status}", self, data)

            if hasattr(self, method):
                self.logger.debug('[%(race)s] Calling status handler for %(status)s' % {
                    'race': self.data.get('name'),
                    'status': status,
                })
                await getattr(self, method)()

        unlisted = self.data.get('unlisted', False)
        if unlisted != self.unlisted:
            if unlisted:
                await RaceRoomService().set_unlisted(self.data.get('name'), self.bot.category_slug)
            else:
                await RaceRoomService().clear_unlisted(self.data.get('name'))
        self.unlisted = unlisted

    # TODO: this should be implemented in the base class
    async def override_stream(self, user):
        """
        Override the streaming requirements for a user.

        `user` should be the hashid of the user.
        """
        payload = {
            'action': 'override_stream',
            'data': {
                'user': user
            }
        }
        if hasattr(self.ws, 'send_json'):
            await self.ws.send_json(payload)
        else:
            await self.ws.send(json.dumps(payload))
        self.logger.info('[%(race)s] overrode stream for %(user)s' % {
            'race': self.data.get('name'),
            'user': user
        })

    async def edit(self, **kwargs):
        """
        Edits the race.  For valid options, see
        https://github.com/racetimeGG/racetime-app/wiki/Category-bots#start-and-edit-races

        This method allows you to only pass what you actually want to change.
        Anything not specified will be pulled from the race room's data.

        Ported from the previously-used fork: upstream ``RaceHandler`` has no
        ``edit`` method. Uses the parent bot's HTTP session and access token to
        POST to the race edit endpoint.
        """
        name = self.data.get('name')
        status = self.data.get('status', {}).get('value')

        if status in ['finished', 'cancelled']:
            # TODO raise a better exception
            raise Exception('Cannot edit a race that has finished or been cancelled.')

        if 'invitational' in kwargs:
            # TODO use a specific error class
            raise Exception('Cannot set invitational status.  Use make_open or make_invitational instead.')

        if kwargs.get('goal') and kwargs.get('custom_goal'):
            # TODO use a specific error class
            raise Exception('Either a goal or custom_goal can be specified, but not both.')

        settings = {}

        if self.data['goal'].get('custom'):
            settings['custom_goal'] = self.data['goal']['name']
        else:
            settings['goal'] = self.data['goal']['name']

        settings['unlisted'] = self.data['unlisted']
        settings['info_user'] = self.data['info_user']
        settings['start_delay'] = round(isodate.parse_duration(self.data['start_delay']).total_seconds())
        settings['time_limit'] = round(isodate.parse_duration(self.data['time_limit']).total_seconds() / 3600)
        settings['streaming_required'] = self.data['streaming_required']
        settings['auto_start'] = self.data['auto_start']
        settings['allow_comments'] = self.data['allow_comments']
        settings['hide_comments'] = self.data.get('hide_comments', False)
        settings['allow_prerace_chat'] = self.data.get('allow_prerace_chat', True)
        settings['allow_midrace_chat'] = self.data['allow_midrace_chat']
        settings['allow_non_entrant_chat'] = self.data['allow_non_entrant_chat']
        settings['chat_message_delay'] = round(isodate.parse_duration(self.data['chat_message_delay']).total_seconds())

        for keyword in kwargs:
            if keyword == 'goal':
                settings[keyword] = kwargs[keyword]
                try:
                    del settings['custom_goal']
                except KeyError:
                    pass
            elif keyword == 'custom_goal':
                settings['custom_goal'] = kwargs['custom_goal']
                try:
                    del settings['goal']
                except KeyError:
                    pass
            else:
                settings[keyword] = kwargs[keyword]

        if status not in ['open', 'invitational']:
            for k in ['goal', 'custom_goal', 'start_delay', 'time_limit', 'streaming_required', 'auto_start', 'allow_prerace_chat']:
                try:
                    del settings[k]
                except KeyError:
                    continue

        try:
            async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(5),
                    retry=retry_if_exception_type(aiohttp.ClientResponseError),
                    wait=wait_exponential(multiplier=1, min=4, max=10)):
                with attempt:
                    async with self.bot.http.post(
                        url=self.bot.http_uri(f'/o/{name}/edit'),
                        data=settings,
                        ssl=self.bot.ssl_context,
                        headers={
                            'Authorization': 'Bearer ' + self.bot.access_token,
                        }
                    ) as resp:
                        if resp.status == 200:
                            return True
        except RetryError as e:
            raise e.last_attempt._exception from e

        raise Exception('Received an unexpected response while editing a race.')

    async def error(self, data):
        await self.send_message(f"Command raised exception: {','.join(data.get('errors'))}")
        # raise Exception(data.get('errors'))

    async def status_in_progress(self):
        await self.send_spoiler_log()
        if self.tournament:
            await self.tournament.on_race_start()

    async def status_pending(self):
        if self.tournament:
            await self.tournament.on_race_pending()

    async def status_open(self):
        pass

    async def status_invitational(self):
        pass

    async def status_finished(self):
        if self.konot:
            await self.konot.create_next_room()

    async def race_data_hook(self):
        pass

    async def intro(self):
        """
        Send introduction messages.
        """
        if not self.state.get('intro_sent'):
            await self.send_message(
                f"Hi!  I'm SahasrahBot, your friendly robotic elder and randomizer seed roller! Use {self.command_prefix}help to see what I can do!   Check out https://sahasrahbot.synack.live/rtgg.html for more info."
            )
            self.state['intro_sent'] = True

    async def end(self):
        # await self.send_message(f"SahasrahBot is now leaving this race room.  Have a great day!")
        self.logger.info(f"Leaving race room {self.data.get('name')}")

    @property
    def teams(self):
        if self.data.get('team_race', False) is False:
            raise Exception('This is not a team race.')

        entrants = [(e['user']['name'], e['team']['name']) for e in self.data['entrants']]
        return {key: [v[0] for v in val] for key, val in
                groupby(sorted(entrants, key=lambda ele: ele[1]), key=lambda ele: ele[1])}

    @property
    def is_equal_teams(self):
        def all_equal(iterable):
            g = groupby(iterable)
            return next(g, True) and not next(g, False)

        teams = self.teams
        return all_equal([len(teams[t]) for t in teams])

    async def ex_cancel(self, args, message):
        self.seed_rolled = False
        await self.set_bot_raceinfo("New Race")
        await self.send_message("Reseting bot state.  You may now roll a new game.")

    async def ex_tournamentrace(self, args, message):
        if await self.is_locked(message):
            return

        # only entrants or race monitors can roll seeds
        if not AuthorizationService().can_roll_tournament_seed(subject_from_message(self, message)):
            await self.send_message(
                'Only entrants or race monitors may roll a tournament seed.'
            )
            return

        if self.tournament:
            await self.tournament.process_tournament_race(args, message)
        else:
            await self.send_message("This room is not associated with a tournament.")

    async def ex_konot(self, args, message):
        await self.send_message(
            "Setting up new KONOT race series!  The last player(s) to finish will be eliminated.  Once this race finishes, a new race will be created and the players advancing will be invited to the new room.")
        await self.set_bot_raceinfo("KONOT Series, Segment #1")
        self.konot = await KONOT.create_new(self.data['category']['slug'], self)

    @monitor_cmd
    async def ex_lock(self, args, message):
        """
        Handle !lock commands.
        Prevent seed rolling unless user is a race monitor.
        """
        self.state['locked'] = True
        await self.send_message(
            'Lock initiated. I will now only roll seeds for race monitors.'
        )

    @monitor_cmd
    async def ex_unlock(self, args, message):
        """
        Handle !unlock commands.
        Remove lock preventing seed rolling unless user is a race monitor.
        """
        self.state['locked'] = False
        await self.send_message(
            'Lock released. Anyone may now roll a seed.'
        )

    async def is_locked(self, message):
        """
        Check if room is locked or seed already exists.
        Post in chat if that is the case.
        """
        if self.seed_rolled:
            await self.send_message(
                'I already rolled a seed!  Use !cancel to clear the currently rolled game.'
            )
            return True
        if self.state.get('locked') and not can_monitor(message):
            await self.send_message(
                'Seed rolling is locked in this room.  Only the creator of this room, a race monitor, or a moderator can roll.'
            )
            return True

        return False

    async def ex_promote(self, args, message):
        if self.tournament:
            racetime_id = message.get('user', {}).get('id', None)
            if await self.tournament.can_gatekeep(racetime_id):
                await self.add_monitor(racetime_id)

    async def ex_override(self, args, message):
        racetime_id = message.get('user', {}).get('id', None)
        racetime_category = self.data['category']['slug']
        whitelisted_user = await RaceRoomService().get_override_whitelist(racetime_id, racetime_category)

        if whitelisted_user is None:
            await self.send_message("You do not have permission to override the stream requirement for this category.  Please contact a category owner if you need this to be changed.")
            return

        if whitelisted_user.expires is not None and whitelisted_user.expires < datetime.utcnow():
            await self.send_message("Your streaming exemption has expired.  Please contact a category owner if you need this to be renewed.")
            return

        await self.override_stream(racetime_id)