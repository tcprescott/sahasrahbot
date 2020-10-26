from racetime_bot import monitor_cmd

from .core import SahasrahBotCoreHandler


class GameHandler(SahasrahBotCoreHandler):
    async def intro(self):
        """
        Send introduction messages.
        """
        if not self.state.get('intro_sent'):
            await self.send_message(
                f"Hi!  I'm SahasrahBot. Use {self.command_prefix}roll to roll your seed (if applicable) and get started!"
            )
            self.state['intro_sent'] = True

    async def ex_roll(self, args, message):
        if await self.is_locked(message):
            return

        await self.send_message("This doesn't do anything yet. (NYI)")
