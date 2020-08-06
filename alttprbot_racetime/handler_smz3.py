from alttprbot.alttprgen import preset
from config import Config as c
from racetime_bot import RaceHandler


class Smz3Handler(RaceHandler):
    """
    SahasrahBot race handler. Generates seeds, presets, and frustration.
    """
    stop_at = ['cancelled', 'finished']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.seed_rolled = False

    async def race_data(self, data):
        self.data = data.get('race')

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
        await self.roll_game(args, message)

    async def ex_race(self, args, message):
        await self.roll_game(args, message)

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!preset <preset>\" to generate a race preset.")

    async def ex_cancel(self, args, message):
        self.seed_rolled = False
        await self.set_raceinfo("New Race", overwrite=True)
        await self.send_message("Reseting bot state.  You may now roll a new game.")

    async def roll_game(self, args, message):
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
            seed, preset_dict = await preset.get_preset(preset_name, randomizer='smz3', spoilers="off")
        except preset.PresetNotFoundException as e:
            await self.send_message(str(e))
            return

        race_info = f"{preset_name} - {seed.url} - ({seed.code})"
        await self.set_raceinfo(race_info)
        await self.send_message(seed.url)
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True
