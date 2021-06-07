from racetime_bot import monitor_cmd

from alttprbot.tournament import sgl
from alttprbot.database import sgl2020_tournament_bo3
from alttprbot.util import speedgaming

from .core import SahasrahBotCoreHandler


class GameHandler(SahasrahBotCoreHandler):
    stop_at = ['cancelled', 'finished']

    async def intro(self):
        """
        Send introduction messages.
        """
        if not self.state.get('intro_sent'):
            await self.send_message(
                f"Hi!  I'm SahasrahBot. Use {self.command_prefix}roll to roll your seed (if applicable) and get started!  If you need help, please contact a SpeedGaming Live admin for assistance."
            )
            self.state['intro_sent'] = True

    async def race_data(self, data):
        self.data = data.get('race')

        if self.data.get('status', {}).get('value') in ['open', 'invitational']:
            await self.intro()

        if self.data.get('status', {}).get('value') == 'in_progress':
            await self.in_progress()

    async def status_in_progress(self):
        await sgl.process_sgl_race_start(self)

    def should_stop(self):
        if self.data.get('status', {}).get('value') in self.stop_at:
            if self.data.get('recordable', False) and self.data.get('recorded', False):
                return True
        return False

    async def ex_roll(self, args, message):
        if await self.is_locked(message):
            return

        await sgl.process_sgl_race(
            handler=self
        )

    async def ex_nextgame(self, args, message):
        await self.send_message("Creating a new race.  Please wait...")
        current_race = await sgl2020_tournament_bo3.get_tournament_race(self.data.get('name'))
        episode_id = current_race['episode_id']
        episode = await speedgaming.get_episode(episode_id)
        url = await sgl.create_sgl_match(episode, force=True)
        await self.send_message(f"New race at {url}")