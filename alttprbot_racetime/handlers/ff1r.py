from alttprbot.alttprgen.randomizer.ffr import roll_ffr

from .core import SahasrahBotCoreHandler

class GameHandler(SahasrahBotCoreHandler):
    async def ex_flags(self, args, message):
        await self.roll_game(args, message)

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!flags <flags>\" to generate a race preset.  Check out https://sahasrahbot.synack.live/rtgg.html for more info.")

    async def roll_game(self, args, message):
        if await self.is_locked(message):
            return

        try:
            flags = args[0]
        except IndexError:
            await self.send_message(
                'You must specify a set of flags!'
            )
            return

        seed_url = roll_ffr(flags)

        await self.set_raceinfo(seed_url)
        await self.send_message(seed_url)
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True
