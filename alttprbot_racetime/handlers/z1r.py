from alttprbot.alttprgen.randomizer.z1r import roll_z1r

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

    async def ex_sglpractice(self, args, message):
        await self.roll_game("VlWlIEwJ1MsKkaOCWhlit2veXNSffs", message)

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!race <preset>\" to generate a seed.  Check out https://sahasrahbot.synack.live/rtgg.html#the-legend-of-zelda-randomizer-z1r for more info.")

    async def roll_game(self, flags, message):
        if await self.is_locked(message):
            return

        seed, flags = roll_z1r(flags)

        await self.set_raceinfo(f"{seed} - {flags}")
        await self.send_message(f"{seed} - {flags}")
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True
