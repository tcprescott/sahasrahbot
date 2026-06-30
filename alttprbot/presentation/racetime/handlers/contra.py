from .core import SahasrahBotCoreHandler


class GameHandler(SahasrahBotCoreHandler):
    async def intro(self):
        await self.send_message("Greetings!  To start a KONOT race, use !konot.")

    async def ex_help(self, args, message):
        await self.send_message("To start a KONOT race, use !konot.")
