import random

from alttprbot.alttprgen.randomizer.z1r import roll_z1r
from .core import SahasrahBotCoreHandler

PRESETS = {
    'abns_swiss': 'J780EYa2ywOnCpVR1VGodM1jVyu!o5F',
    'abns_bracket': 'PPcIk!s3aupL7C41f6AhZ3mi8IwACwv',
    'abns_elite8': 'PPcIk!s3aupL9yxEvapydBFdC9X8E2A',
    'consternation': 'ItRtYLs2xToBiCHEvfcY6eRIcxG!VfM'
}


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

    async def ex_z1rtournament(self, args, message):
        seed_number = random.randint(0, 9999999999999999)
        await self.send_message(f"Z1R 2024 Tournament - Flags: ItRtYcBhrKWVT6C67oOLsUpgEaHopla Seed: {seed_number}")
        await self.set_bot_raceinfo(f"Flags: ItRtYcBhrKWVT6C67oOLsUpgEaHopla Seed: {seed_number}")

    async def ex_race(self, args, message):
        seed_number = random.randint(0, 9999999999999999)
        try:
            preset = args[0]
            flags = PRESETS[preset]
        except KeyError:
            await self.send_message("Invalid preset specified.")
            return
        except IndexError:
            await self.send_message("No preset specified.")

        await self.send_message(f"{preset} - Flags: {flags} Seed: {seed_number}")
        await self.set_bot_raceinfo(f"Flags: {flags} Seed: {seed_number}")

    async def ex_help(self, args, message):
        await self.send_message(
            "Available commands:\n\"!race <preset>\" to generate a seed.  Check out https://sahasrahbot.synack.live/rtgg.html#the-legend-of-zelda-randomizer-z1r for more info.")

    async def roll_game(self, flags, message):
        if await self.is_locked(message):
            return

        seed, flags = roll_z1r(flags)

        await self.set_bot_raceinfo(f"Seed: {seed} - Flags: {flags}")
        await self.send_message(f"Seed: {seed} - Flags: {flags}")
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True
