from .core import SahasrahBotCoreHandler


class GameHandler(SahasrahBotCoreHandler):
    async def ex_help(self, args, message):
        await self.send_message("I have no commands for this category.")
