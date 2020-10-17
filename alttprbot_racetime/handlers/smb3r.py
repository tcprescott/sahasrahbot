from alttprbot.alttprgen.randomizer.smb3r import roll_smb3r

from .core import SahasrahBotCoreHandler

class GameHandler(SahasrahBotCoreHandler):
    async def ex_flags(self, args, message):
        await self.roll_game(args, message)

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!flags <flags>\" to generate a race preset.  Check out https://sahasrahbot.synack.live/rtgg.html for more info.")

    async def ex_cancel(self, args, message):
        self.seed_rolled = False
        await self.set_raceinfo("New Race", overwrite=True)
        await self.send_message("Reseting bot state.  You may now roll a new game.")

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

        seed, flags = roll_smb3r(flags)

        await self.set_raceinfo(f"{seed} - {flags}")
        await self.send_message(f"{seed} - {flags}")
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True
