from alttprbot.alttprgen import preset
from config import Config as c
from racetime_bot import RaceHandler, monitor_cmd, can_monitor


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

        if self.data.get('status', {}).get('value') in ['open', 'invitational']:
            await self.intro()

    async def intro(self):
        """
        Send introduction messages.
        """
        if not self.state.get('intro_sent') and not c.DEBUG:
            await self.send_message(
                f"Hi!  I'm SahasrahBot, your friendly robotic elder and ALTTPR/SMZ3 seed roller! Use {self.command_prefix}help to see what I can do!   Check out https://sahasrahbot.synack.live/rtgg.html for more info."
            )
            self.state['intro_sent'] = True

    async def ex_preset(self, args, message):
        await self.roll_game(args, message)

    async def ex_race(self, args, message):
        await self.roll_game(args, message)

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!race <preset>\" to generate a race preset.  Check out https://sahasrahbot.synack.live/rtgg.html for more info.")

    async def ex_cancel(self, args, message):
        self.seed_rolled = False
        await self.set_raceinfo("New Race", overwrite=True)
        await self.send_message("Reseting bot state.  You may now roll a new game.")

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

    async def roll_game(self, args, message):
        if self.seed_rolled:
            await self.send_message(
                'I already rolled a seed!  Use !cancel to clear the currently rolled game.'
            )
            return
        if self.state.get('locked') and not can_monitor(message):
            await self.send_message(
                'Seed rolling is locked in this room.  Only the creator of this room, a race monitor, or a moderator can roll.'
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
