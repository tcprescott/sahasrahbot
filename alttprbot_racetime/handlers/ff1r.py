from alttprbot.alttprgen.randomizer.ffr import roll_ffr

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

    async def ex_sglpods(self, args, message):
        await self.roll_game("yGcifaseK8fJxIkkAzUzYAzx32UoP5toiyJrTE864J9FEyMsXe5XhM5T94nANOh1T6wJN7BZU4p3r3WORe9o7vyXSpZD", message)

    async def ex_sglbrackets(self, args, message):
        await self.roll_game("yGq4dTUZierDQgQt0W-opZBxIHu3Djls2qM3uv02Y6KFCBgdRRG1fVdgyOD!kw3MO9U-Ez9vU4p3r3WORe9o7vyXSpZD", message)

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!flags <flags>\" to generate seed.  Check out https://sahasrahbot.synack.live/rtgg.html#final-fantasy-randomizer-ff1r for more info.")

    async def roll_game(self, flags, message):
        if await self.is_locked(message):
            return

        seed_url, flags = roll_ffr(flags)

        await self.set_raceinfo(seed_url)
        await self.send_message(seed_url)
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True
