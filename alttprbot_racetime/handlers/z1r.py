import random

from alttprbot.alttprgen.randomizer.z1r import roll_z1r
from .core import SahasrahBotCoreHandler

PRESETS = {
    'abns_swiss': 'J780EYa2ywOnCpVR1VGodM1jVyu!o5F',
    'abns_bracket': 'PPcIk!s3aupL7C41f6AhZ3mi8IwACwv',
    'abns_elite8': 'PPcIk!s3aupL9yxEvapydBFdC9X8E2A',
    'consternation': 'ItRtYLs2xToBiCHEvfcY6eRIcxG!VfM',
    '2019brackets': 'ItRtYLs2xC69xBrSRTzj6AW6Ja0fcbv',
    'rr2024': 'NuJS0dpRgVdyn25HEl8NnSW7WSfLf9v2M',
    'sgl24': '9FtgnrOp3JvLxvq1Bf4xtluLDpuXvRQm2',
    'bettypls': 'EOYppQG7Q8X5I1tNsFH8R!jOlpTT3x1tx',
    'excavator': 'voSNknIvGu68ic41GpP4kXSjCqtAN2kNq',
    'jesscherk': 'ItRtYM3auE3OVFlt6lBQK7khitoHMaU',
    'magsrush': 'NNxPDPcF9p56THwiFFsHmx7x8Qod2km41',
    'babysfirsthdn': 'Iv4gW3YU!vlmAtgUOMAM49fslZQS0ed',
    'walkitin': '6xEziMRCF!vbiyFjZTUYKxi1V80R30fqo',
    'swordlessplus': 'IVTU8pFHFatE6exqwxuIWuC9GkDFxAAk1',
    'randomforce': 'M16vlklqs4RtcAYYE4Pqo8CAB1a5HWing3'
}
# A note on 2019 brackets. The flag string in Zelda Randomizer is missing
# Recorder to New Dungeons and Shuffle Overworld Group, which were ON.
# The flag string above turns those on, along with Race ROM.

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

    async def ex_randomforce(self, args, message):
        if await self.is_locked(message):
            return
        
        flags = PRESETS['randomforce']
        seed_number, flags = roll_z1r(flags)

        await self.send_message(f"2025 Z1R Winter Tournament - Flags: {flags} Seed: {seed_number}")
        await self.set_bot_raceinfo(f"Flags: {flags} Seed: {seed_number}")
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True

    # Individual commands for these Triforce Triple Play Season 2 flags as requested.
    async def ex_bettypls(self, args, message):
        await self.ex_race(['bettypls'], message)
    
    async def ex_excavator(self, args, message):
        await self.ex_race(['excavator'], message)

    async def ex_jesscherk(self, args, message):
        await self.ex_race(['jesscherk'], message)

    async def ex_magsrush(self, args, message):
        await self.ex_race(['magsrush'], message)

    async def ex_babysfirsthdn(self, args, message):
        await self.ex_race(['babysfirsthdn'], message)

    async def ex_walkitin(self, args, message):
        await self.ex_race(['walkitin'], message)

    async def ex_swordlessplus(self, args, message):
        await self.ex_race(['swordlessplus'], message)

    async def ex_ttp2(self, args, message):
        # Choose a Triforce Triple Play Season 2 flag string at random.
        flag_choice = random.randint(1, 7)
        
        if flag_choice == 1:
            await self.ex_race(['bettypls'], message)
        elif flag_choice == 2:
            await self.ex_race(['excavator'], message)
        elif flag_choice == 3:
            await self.ex_race(['jesscherk'], message)
        elif flag_choice == 4:
            await self.ex_race(['magsrush'], message)
        elif flag_choice == 5:
            await self.ex_race(['babysfirsthdn'], message)
        elif flag_choice == 6:
            await self.ex_race(['walkitin'], message)
        else:
            await self.ex_race(['swordlessplus'], message)
    
    async def ex_race(self, args, message):
        if await self.is_locked(message):
            return
        
        try:
            preset = args[0]
            flags = PRESETS[preset]
        except KeyError:
            await self.send_message("Invalid preset specified.")
            return
        except IndexError:
            await self.send_message("No preset specified.")
            return

        seed_number, flags = roll_z1r(flags)
        
        await self.send_message(f"{preset} - Flags: {flags} Seed: {seed_number}")
        await self.set_bot_raceinfo(f"Flags: {flags} Seed: {seed_number}")
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True

    async def ex_help(self, args, message):
        await self.send_message(
            "Available commands:\n\"!race <preset>\" or \"!flags <flagstring>\" to generate a seed.  Check out https://sahasrahbot.synack.live/rtgg.html#the-legend-of-zelda-randomizer-z1r for more info.")

    async def roll_game(self, flags, message):
        if await self.is_locked(message):
            return

        seed, flags = roll_z1r(flags)

        await self.set_bot_raceinfo(f"Seed: {seed} - Flags: {flags}")
        await self.send_message(f"Seed: {seed} - Flags: {flags}")
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True
