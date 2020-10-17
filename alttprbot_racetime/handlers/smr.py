from alttprbot.alttprgen import preset, smvaria
from alttprbot.alttprgen.randomizer import roll_smdash
from pyz3r.exceptions import UnableToRetrieve, UnableToGenerate

from .core import SahasrahBotCoreHandler

class GameHandler(SahasrahBotCoreHandler):
    async def ex_totalrace(self, args, message):
        if await self.is_locked(message):
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
            seed, preset_dict = await preset.get_preset(preset_name, randomizer='sm', spoilers="off")
        except preset.PresetNotFoundException as e:
            await self.send_message(str(e))
            return

        race_info = f"SM Total Randomizer - {preset_name} - {seed.url} - ({seed.code})"
        await self.set_raceinfo(race_info)
        await self.send_message(seed.url)
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True

    async def ex_variarace(self, args, message):
        if await self.is_locked(message):
            return

        try:
            settings = args[0],
            skills = args[1]
        except IndexError:
            await self.send_message(
                'You must specify setting and skill presets!'
            )
            return

        await self.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")
        try:
            seed = await smvaria.generate_preset(
                settings=settings,
                skills=skills,
                race=True
            )
        except (UnableToRetrieve, UnableToGenerate) as e:
            await self.send_message(str(e))
            return

        await self.set_raceinfo(f"SM VARIA Randomizer - {settings} / {skills} - {seed.url}")
        await self.send_message(seed.url)
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True

    async def ex_dashrace(self, args, message):
        if await self.is_locked(message):
            return

        seed = roll_smdash()

        await self.set_raceinfo(f"SM Dash Randomizer - seed: {seed}")
        await self.send_message(f"{seed}")
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!totalrace <preset>, !variarace <settings> <skills>, !dashrace\" to generate a seed.  Check out https://sahasrahbot.synack.live/rtgg.html#super-mario-bros-3-randomizer-smb3r for more info.")
