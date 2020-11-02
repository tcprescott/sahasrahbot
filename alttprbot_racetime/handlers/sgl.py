from racetime_bot import monitor_cmd

from alttprbot.tournament import sgl

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

    async def race_data(self, data):
        self.data = data.get('race')

        if self.data.get('status', {}).get('value') in ['open', 'invitational']:
            await self.intro()

        if self.data.get('status', {}).get('value') == 'in_progress':
            await self.in_progress()

    async def in_progress(self):
        await sgl.process_sgl_race_start(self)

    async def ex_roll(self, args, message):
        if await self.is_locked(message):
            return

        await sgl.process_sgl_race(
            handler=self
        )
