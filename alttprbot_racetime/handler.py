import asyncio
import math

from alttprbot.alttprgen import mystery, preset, spoilers
from alttprbot.database import spoiler_races
from config import Config as c
from racetime_bot import RaceHandler, monitor_cmd, can_monitor


class AlttprHandler(RaceHandler):
    """
    SahasrahBot race handler. Generates seeds, presets, and frustration.
    """
    stop_at = ['cancelled', 'finished']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.seed_rolled = False

    async def begin(self):
        self.state['locked'] = False

    async def error(self, data):
        await self.send_message(f"Command raised exception: {','.join(data.get('errors'))}")

    async def race_data(self, data):
        self.data = data.get('race')

        if self.data.get('status', {}).get('value') == 'in_progress':
            await self.in_progress()

        if self.data.get('status', {}).get('value') in ['open', 'invitational']:
            await self.intro()

    async def in_progress(self):
        await self.send_spoiler_log()

    async def intro(self):
        if not self.state.get('intro_sent') and not c.DEBUG:
            await self.send_message(
                f"Hi!  I'm SahasrahBot, your friendly robotic elder and ALTTPR/SMZ3 seed roller! Use {self.command_prefix}help to see what I can do!  Check out https://sahasrahbot.synack.live/rtgg.html for more info."
            )
            self.state['intro_sent'] = True

    async def ex_preset(self, args, message):
        try:
            preset_name = args[0]
        except IndexError:
            await self.send_message(
                'You must specify a preset!'
            )
            return
        await self.roll_game(preset_name=preset_name, message=message, allow_quickswap=False)

    async def ex_race(self, args, message):
        try:
            preset_name = args[0]
        except IndexError:
            await self.send_message(
                'You must specify a preset!'
            )
            return
        await self.roll_game(preset_name=preset_name, message=message, allow_quickswap=False)

    @monitor_cmd
    async def ex_sglqual(self, args, message):
        if self.data.get('status', {}).get('value') == 'open':
            await self.set_invitational()

        await self.roll_game(preset_name='openboots', message=message, allow_quickswap=True)

    async def ex_quickswaprace(self, args, message):
        try:
            preset_name = args[0]
        except IndexError:
            await self.send_message(
                'You must specify a preset!'
            )
            return
        await self.roll_game(preset_name=preset_name, message=message, allow_quickswap=True)

    async def ex_spoiler(self, args, message):
        if self.seed_rolled:
            await self.send_message(
                'I already rolled a seed!'
            )
            return

        try:
            preset_name = args[0]
        except IndexError:
            await self.send_message(
                'You must specify a preset!'
            )
            return

        await self.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")
        try:
            seed, preset_dict, spoiler_log_url = await spoilers.generate_spoiler_game(preset_name)
        except preset.PresetNotFoundException as e:
            await self.send_message(str(e))
            return

        try:
            studytime = args[1]
        except IndexError:
            studytime = preset_dict.get('studytime', 900)

        await self.set_raceinfo(f"spoiler {preset_name} - {seed.url} - ({'/'.join(seed.code)})")
        await self.send_message(seed.url)
        await self.send_message(f"The spoiler log for this race will be sent after the race begins in this room.  A {studytime}s countdown timer at that time will begin.")
        await spoiler_races.insert_spoiler_race(self.data.get('name'), spoiler_log_url, studytime)
        self.seed_rolled = True

    async def ex_mystery(self, args, message):
        if self.seed_rolled:
            await self.send_message(
                'I already rolled a seed!'
            )
            return
        if self.state.get('locked') and not can_monitor(message):
            await self.send_message(
                'Seed rolling is locked in this room.  Only the creator of this room, a race monitor, or a moderator can roll.'
            )
            return
        weightset = args[0] if args else 'weighted'

        await self.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")
        try:
            seed = await mystery.generate_random_game(
                weightset=weightset,
                tournament=True,
                spoilers="mystery"
            )
        except mystery.WeightsetNotFoundException as e:
            await self.send_message(str(e))
            return

        await self.set_raceinfo(f"mystery {weightset} - {seed.url} - ({'/'.join(seed.code)})")
        await self.send_message(seed.url)
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True

    @monitor_cmd
    async def ex_cancel(self, args, message):
        self.seed_rolled = False
        await self.set_raceinfo("New Race", overwrite=True)
        await self.send_message("Reseting bot state.  You may now roll a new game.")

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!race <preset>\" to generate a race preset.\n\"!mystery <weightset>\" to generate a mystery game.\n\"!spoiler <preset>\" to generate a spoiler race.  Check out https://sahasrahbot.synack.live/rtgg.html for more info.")

    async def ex_register(self, args, message):
        await self.send_message("Lazy Kid ain't got nothing compared to me.")

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

    async def send_spoiler_log(self):
        name = self.data.get('name')
        race = await spoiler_races.get_spoiler_race_by_id(name)
        if race:
            await spoiler_races.delete_spoiler_race(name)
            await self.send_message('Sending spoiler log...')
            await self.send_message('---------------')
            await self.send_message(f"This race\'s spoiler log: {race['spoiler_url']}")
            await self.send_message('---------------')
            await self.send_message('GLHF! :mudora:')
            await self.countdown_timer(
                duration_in_seconds=race['studytime'],
                beginmessage=True,
            )

    async def countdown_timer(self, duration_in_seconds, beginmessage=False):
        loop = asyncio.get_running_loop()

        reminders = [1800, 1500, 1200, 900, 600, 300,
                     120, 60, 30, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
        start_time = loop.time()
        end_time = loop.time() + duration_in_seconds
        while True:
            # print(datetime.datetime.now())
            timeleft = math.ceil(
                start_time - loop.time() + duration_in_seconds)
            # print(timeleft)
            if timeleft in reminders:
                minutes = math.floor(timeleft/60)
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
            await asyncio.sleep(.5)

    async def roll_game(self, preset_name, message, allow_quickswap=False):
        if self.seed_rolled:
            await self.send_message(
                'I already rolled a seed! Use !cancel to clear the currently rolled game'
            )
            return
        if self.state.get('locked') and not can_monitor(message):
            await self.send_message(
                'Seed rolling is locked in this room.  Only the creator of this room, a race monitor, or a moderator can roll.'
            )
            return

        await self.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")
        try:
            seed, preset_dict = await preset.get_preset(preset_name, randomizer='alttpr', spoilers="off", allow_quickswap=allow_quickswap)
        except preset.PresetNotFoundException as e:
            await self.send_message(str(e))
            return

        race_info = f"{preset_name} - {seed.url} - ({'/'.join(seed.code)})"
        if allow_quickswap:
            race_info += " - Quickswap Enabled"
        await self.set_raceinfo(race_info)
        await self.send_message(seed.url)
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True
