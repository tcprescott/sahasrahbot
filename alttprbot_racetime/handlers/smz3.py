from alttprbot.alttprgen import preset

from .core import SahasrahBotCoreHandler

class GameHandler(SahasrahBotCoreHandler):
    async def ex_preset(self, args, message):
        await self.roll_game(args, message)

    async def ex_race(self, args, message):
        await self.roll_game(args, message)

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!race <preset>\" to generate a race preset.  Check out https://sahasrahbot.synack.live/rtgg.html#smz3-commands for more info.")

    async def roll_game(self, args, message):
        if await self.is_locked(message):
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
