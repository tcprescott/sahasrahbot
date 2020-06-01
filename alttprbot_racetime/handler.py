import asyncio
import math

from alttprbot.alttprgen import mystery, preset, spoilers
from alttprbot.database import spoiler_races
from config import Config as c
from racetime_bot import RaceHandler


class AlttprHandler(RaceHandler):
    """
    SahasrahBot race handler. Generates seeds, presets, and frustration.
    """
    stop_at = ['cancelled', 'finished']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.seed_rolled = False

    async def race_data(self, data):
        self.data = data.get('race')

        if self.data.get('status', {}).get('value') == 'in_progress':
            await self.in_progress()

    async def in_progress(self):
        await self.send_spoiler_log()

    async def begin(self):
        """
        Send introduction messages.
        """
        if not self.state.get('intro_sent') and not c.DEBUG:
            await self.send_message(
                f"Hi!  I'm SahasrahBot, your friendly robotic elder and ALTTPR/SMZ3 seed roller! Use {self.command_prefix}help to see what I can do!"
            )
            self.state['intro_sent'] = True

    async def ex_preset(self, args, message):
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
            seed, preset_dict = await preset.get_preset(preset_name, randomizer='alttpr', spoilers="off")
        except preset.PresetNotFoundException as e:
            await self.send_message(str(e))
            return
        await self.set_raceinfo(f"{preset_name} - {seed.url} - ({'/'.join(seed.code)})")
        await self.send_message(seed.url)
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True

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

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!preset <preset>\" to generate a race preset.\n\"!mystery <weightset>\" to generate a mystery game.\n\"!spoiler <preset>\" to generate a spoiler race.")

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
            timeleft = math.ceil(start_time - loop.time() + duration_in_seconds)
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
