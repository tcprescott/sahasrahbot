from alttprbot.alttprgen.randomizer.smb3r import roll_smb3r

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

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!flags <flags>\" to generate a seed.  Check out https://sahasrahbot.synack.live/rtgg.html#super-mario-bros-3-randomizer-smb3r for more info.")

    async def roll_game(self, flags, message):
        if await self.is_locked(message):
            return

        seed, flags = roll_smb3r(flags)

        await self.set_raceinfo(f"{seed} - {flags}")
        await self.send_message(f"{seed} - {flags}")
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True
