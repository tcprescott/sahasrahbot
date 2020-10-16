from racetime_bot import RaceHandler, monitor_cmd


class SGLHandler(RaceHandler):
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
        if not self.state.get('intro_sent'):
            await self.send_message(
                f"Hi!  I'm SahasrahBot. Use {self.command_prefix}roll to roll your seed (if applicable) and get started!"
            )
            self.state['intro_sent'] = True

    @monitor_cmd
    async def ex_roll(self, args, message):
        await self.send_message("This doesn't do anything yet. (NYI)")
