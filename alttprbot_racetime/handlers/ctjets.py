from alttprbot.alttprgen import generator

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

        seed = await generator.CTJetsPreset(preset).generate()

        await self.send_message(seed)
        await self.set_bot_raceinfo(seed)
        await self.send_message("Seed rolling complete.  See race info for details.")

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!preset <preset>\" to generate a seed.")
