from alttprbot.alttprgen.randomizer import ctjets

from .core import SahasrahBotCoreHandler


class GameHandler(SahasrahBotCoreHandler):
    async def ex_preset(self, args, message):
        if await self.is_locked(message):
            return

        try:
            preset = args[0]
        except IndexError:
            await self.send_message(
                'You must specify a preset!'
            )
            return

        await self.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")

        preset_dict = await ctjets.fetch_preset(preset)

        seed = await ctjets.roll_ctjets(
            version=preset_dict.get('version', '3.1.0'),
            settings=preset_dict['settings']
        )

        await self.send_message(seed)
        await self.set_raceinfo(seed)
        await self.send_message("Seed rolling complete.  See race info for details.")

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!preset <preset>\" to generate a seed.")
