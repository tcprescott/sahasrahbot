from alttprbot.alttprgen.randomizer.ffr import roll_ffr

from .core import SahasrahBotCoreHandler


class GameHandler(SahasrahBotCoreHandler):
    async def ex_ff1url(self, args, message):
        try:
            url = args[0]
        except IndexError:
            await self.send_message(
                'You must specify a FF1R URL with the flags!'
            )
            return

        await self.roll_game(url, message)

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!ff1url <url>\" to generate seed.  Check out https://sahasrahbot.synack.live/rtgg.html#final-fantasy-randomizer-ff1r for more info.")

    async def roll_game(self, flags, message):
        if await self.is_locked(message):
            return

        _, seed_url = roll_ffr(flags)

        await self.set_bot_raceinfo(seed_url)
        await self.send_message(seed_url)
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True
