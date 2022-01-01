import random
from .core import SahasrahBotCoreHandler
from alttprbot.alttprgen.randomizer import z2r

class GameHandler(SahasrahBotCoreHandler):
    async def ex_flags(self, args, message):
        try:
            flags = args[0]
        except IndexError:
            await self.send_message(
                'You must specify a set of flags!'
            )
            return

        if await self.is_locked(message):
            return

        seed = random.randint(0, 1000000000)
        await self.set_raceinfo(f"Seed: {seed} - Flags: {flags}")
        await self.send_message(f"Seed: {seed} - Flags: {flags}")

        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True

    async def ex_mrb(self, args, message):
        if await self.is_locked(message):
            return

        seed, flags, description = z2r.mrb()

        await self.set_raceinfo(f"Seed: {seed} - Flags: {flags} - {description}")
        await self.send_message(f"Seed: {seed} - Flags: {flags} - {description}")

        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True

    async def ex_maxrando(self, args, message):
        await self.roll_game('maxrando', message)

    async def ex_groups1(self, args, message):
        await self.roll_game('groups1', message)

    async def ex_groups2(self, args, message):
        await self.roll_game('groups2', message)

    async def ex_groups3(self, args, message):
        await self.roll_game('groups3', message)

    async def ex_groups4(self, args, message):
        await self.roll_game('groups4', message)

    async def ex_brackets(self, args, message):
        await self.roll_game('brackets', message)

    async def ex_nit(self, args, message):
        await self.roll_game('nit', message)

    async def ex_sgl4(self, args, message):
        await self.roll_game('sgl4', message)

    async def ex_sgl(self, args, message):
        await self.roll_game('sgl', message)

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!flags <flags>\" to generate a seed.  Check out https://sahasrahbot.synack.live/rtgg.html#zelda-2-randomizer-z2r for more info.")

    async def roll_game(self, preset, message):
        if await self.is_locked(message):
            return

        seed, flags = z2r.preset(preset)

        await self.set_raceinfo(f"Seed: {seed} - Flags: {flags}")
        await self.send_message(f"Seed: {seed} - Flags: {flags}")

        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True
