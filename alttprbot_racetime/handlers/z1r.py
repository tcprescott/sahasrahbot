import random

from alttprbot.alttprgen.randomizer.z1r import roll_z1r
from .core import SahasrahBotCoreHandler

PRESETS = {
    'abns22_swiss': 'oIbnPfPb01HJEAN8LBIMmlBWz!gGeqNjpYphk',
    'abns22_bracket': '143oNtDD4RQLqGPLpaSfjC2AnRmLOpqFAW5QT4',
    'abns22_top8': '143oNtDD4RQLrJy5BfGRUWmqGpjvyjX29Xj97o',
    'consternation': 'oIbnPfPb01Hll3D29Bc2!etrojQOSjJQZUJ3A',
    '2019brackets': 'oIbnPfPaymqfyH4t7pgvRD4cP1H1I7sPTblX9',
    'rr2024': 'oIbq2JttN3ae9PzaCJOsVpXedaDD1C2B1yAt8',
    'sgl24': 'oIbnPfPb01HmodtgCWCvSuAbuHPqZRIVKCvKj',
    'bettypls': 'q9yBZxHDLh6lovXqLgSNrmEieda2tqJLXZUEo',
    'excavator': 'hvFx!4yyHzSQ4RIGBlC82EgnMP0hKMULyMo0WP',
    'jesscherk': 'oIbnPg!o7RsFZtKnEc9AAI8WI7bpnQVS16uNU',
    'magsrush': 'oIbnPfPb01Hll3F1P2W2uMZOcOJWr!jS05L0A',
    'babysfirsthdn': 'oVeI512duFh1JQJ6dol1rhfGazsxVWEBeazWF',
    'walkitin': 'oIbnPfPaymqfyH3OJhgiKHew0nr6Guj6lqHtv',
    'swordlessplus': 'oIbnPfPb01Hns9ilYf3aXrUwNv7SZU05a56UV',
    'randomforce': 'oIbnPfPazW!1troLaKovLCWdzL0Ech79PCP7x',
    'rr2025': 'CKnGZ6u7XaVW!hJ!sGTvkRim82t8PvIW1BEycZo',
    'sgl25online': '12TDBJOu7zgjkBGTDwHViA9wS3IpdJcvhCVEtu9',
    'power': '143oNtDD4PAvBt5G8xyCFu5kwp7tS8vUBVpiZY',
    'courage': 'oIbnQLMCpyScZbUVFbgpGKPLsHFflaoYKIxoA',
    'wisdom': 'oIbnPfPb0mR7ggY12zwI0QNIY620UnhU8kiC3',
    'sgl25ip': '12TDBJOu7zgjkBGTDsoDP5Hg7jnJNmTUCh4wT9X',
    'ttp4rp': '24hJoDaoq92qaumIfio4Qq8LtfU0Xt8tpG3Iafo',
    'ttp4hopla': 'oIbnRjuMUKqwdnOXzOMO7PuDtwAvU3boJnaXW',
    'ttp4consternation': 'oIbnPfPb01Hll3D295IGDxxjR4UwfEok8P4MD',
    'afbns_swiss': '1K9hKZCQamJvAprO0CLKqHgZk0MR1RqiE9bfe9xv',
    'afbns_bracket': '12V4XiZA!b3mWgwigt9JQcwZSUlpadoHsJNny3J',
    'afbns_top8': '12V4XiZA!b3mWh!GQFcZr9rUkzjsoaFlYFS64EU'
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

    # Individual commands for these Triforce Triple Play Season 4 flags as requested.
    async def ex_ttp4rp(self, args, message):
        await self.ex_race(['ttp4rp'], message)
    
    async def ex_ttp4hopla(self, args, message):
        await self.ex_race(['ttp4hopla'], message)

    async def ex_ttp4consternation(self, args, message):
        await self.ex_race(['ttp4consternation'], message)

    async def ex_ttp4(self, args, message):
        # Choose a Triforce Triple Play Season 4 flag string at random.
        flag_choice = random.randint(1, 3)
        
        if flag_choice == 1:
            await self.ex_race(['ttp4rp'], message)
        elif flag_choice == 2:
            await self.ex_race(['ttp4hopla'], message)
        else:
            await self.ex_race(['ttp4consternation'], message)

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
