from alttprbot.alttprgen import generator

from .core import MSG_GENERATING, MSG_NO_PRESET, MSG_ROLL_COMPLETE, SahasrahBotCoreHandler


class GameHandler(SahasrahBotCoreHandler):
    async def ex_preset(self, args, message):
        if await self.is_locked(message):
            return

        try:
            preset = args[0]
        except IndexError:
            await self.send_message(
                MSG_NO_PRESET
            )
            return

        await self.send_message(MSG_GENERATING)

        seed = await generator.CTJetsPreset(preset).generate()

        await self.send_message(seed)
        await self.set_bot_raceinfo(seed)
        await self.send_message(MSG_ROLL_COMPLETE)

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!preset <preset>\" to generate a seed.")
