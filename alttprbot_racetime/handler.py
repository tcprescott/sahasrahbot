from racetime_bot import RaceHandler
from alttprbot.alttprgen import mystery, preset, spoilers

class AlttprHandler(RaceHandler):
    """
    SahasrahBot race handler. Generates seeds, presets, and frustration.
    """
    stop_at = ['cancelled', 'finished']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.seed_rolled = False

    async def begin(self):
        """
        Send introduction messages.
        """
        if not self.state.get('intro_sent'):
            await self.send_message(
                "Hi!  I'm SahasrahBot, your friendly robotic elder and ALTTPR/SMZ3 seed roller! Create a seed with !preset <preset>"
            )
            self.state['intro_sent'] = True

    async def ex_preset(self, args, message):
        if self.seed_rolled:
            await self.send_message(
                'I already rolled a seed!'
            )
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
            seed, preset_dict = await preset.get_preset(preset_name, randomizer='alttpr', spoilers="off")
        except preset.PresetNotFoundException as e:
            await self.send_message(str(e))
            return
        await self.set_raceinfo(f"{preset_dict.get('goal_name', 'unknown')} - {seed.url} - ({'/'.join(seed.code)})")
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True

    async def ex_mystery(self, args, message):
        if self.seed_rolled:
            await self.send_message(
                'I already rolled a seed!'
            )
            return
        weightset = args[0] if args else 'weighted'

        await self.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")
        try:
            seed = await mystery.generate_random_game(
                weightset=weightset,
                tournament=True,
                spoilers="mystery"
            )
        except mystery.WeightsetNotFoundException as e:
            await self.send_message(str(e))
            return

        await self.set_raceinfo(f"mystery {weightset} - {seed.url} - ({'/'.join(seed.code)})")
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True
