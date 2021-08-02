import random
from .core import SahasrahBotCoreHandler


class GameHandler(SahasrahBotCoreHandler):
    async def ex_flags(self, args, message):
        try:
            flags = args[0]
        except IndexError:
            await self.send_message(
                'You must specify a set of flags!'
            )
            return

        await self.roll_game(flags, message)

    async def ex_maxrando(self, args, message):
        await self.roll_game('iyhqh$j9g7@$ZqTBT!BhOAdES$@', message)

    async def ex_groups1(self, args, message):
        await self.roll_game('jhAhD0L#$Za$LpTBT!AhOA!0P@@', message)

    async def ex_groups2(self, args, message):
        await self.roll_game('jhAhD0L#$Z8$LpTBT!AhOA!0P@@', message)

    async def ex_groups3(self, args, message):
        await self.roll_game('hhAhD0L#$Za$LpTBT!AhOA!0P@@', message)

    async def ex_groups4(self, args, message):
        await self.roll_game('hhAhD0L#$Z8$LpTBT!AhOA!0P@@', message)

    async def ex_brackets(self, args, message):
        await self.roll_game('hhAhD0j#$78$Jp5HgRAhOA!0P8@', message)

    async def ex_nit(self, args, message):
        await self.roll_game('hhAhD0j#$78$Jp5Q$dAhOA!0Pz@A', message)

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!flags <flags>\" to generate a seed.  Check out https://sahasrahbot.synack.live/rtgg.html#zelda-2-randomizer-z2r for more info.")

    async def roll_game(self, flags, message):
        if await self.is_locked(message):
            return

        seed = random.randint(0, 1000000000)

        await self.set_raceinfo(f"Seed: {seed} - Flags: {flags}")
        await self.send_message(f"Seed: {seed} - Flags: {flags}")
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True
