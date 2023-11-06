import random

from alttprbot.alttprgen import generator, smz3multi
from .core import SahasrahBotCoreHandler


class GameHandler(SahasrahBotCoreHandler):
    async def ex_multiworld(self, args, message):
        if await self.is_locked(message):
            return

        try:
            preset_name = args[0]
        except IndexError:
            await self.send_message(
                'You must specify a preset!'
            )
            return

        try:
            seed_number = int(args[1])
            if seed_number < 0 or seed_number > 2147483647:
                raise ValueError("Seed number must be between 0 and 2147483647")
        except IndexError:
            seed_number = random.randint(0, 2147483647)

        if self.data.get('team_race', False) is False:
            await self.send_message('This must be a team race.')
            return

        if not self.is_equal_teams:
            await self.send_message("Teams are unequal in size.")
            return

        await self.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")

        try:
            teams = self.teams
            for team in teams:
                seed = await smz3multi.generate_multiworld(preset_name, teams[team], tournament=True, randomizer='smz3', seed_number=seed_number)
                await self.send_message(f"Team {team}: {seed.url}")
                await self.send_message("------")
        except Exception as e:
            await self.send_message(str(e))
            return

        race_info = f"SMZ3 Multiworld - {preset_name}"
        await self.set_bot_raceinfo(race_info)
        await self.send_message("Seed rolling complete.")
        self.seed_rolled = True

    async def ex_preset(self, args, message):
        await self.roll_game(args, message)

    async def ex_race(self, args, message):
        await self.roll_game(args, message)

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!race <preset>, !multiworld <preset>\" to generate a race preset.  Check out https://sahasrahbot.synack.live/rtgg.html#smz3-commands for more info.")

    async def roll_game(self, args, message):
        if await self.is_locked(message):
            return

        try:
            preset_name = args[0]
        except IndexError:
            await self.send_message(
                'You must specify a preset!'
            )
            return

        await self.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")

        smz3preset = generator.SMZ3Preset(preset_name)
        await smz3preset.generate(tournament=True, spoilers=False)

        race_info = f"{preset_name} - {smz3preset.seed.url} - ({smz3preset.seed.code})"
        await self.set_bot_raceinfo(race_info)
        await self.send_message(smz3preset.seed.url)
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True

    async def ex_spoiler(self, args, message):
        if await self.is_locked(message):
            return

        try:
            preset_name = args[0]
        except IndexError:
            await self.send_message(
                'You must specify a preset!'
            )
            return

        await self.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")
        smz3preset = generator.SMZ3Preset(preset_name)
        await smz3preset.generate(tournament=True, spoilers=True)
        spoiler_url = smz3preset.spoiler_url()

        try:
            studytime = int(args[1])
        except IndexError:
            studytime = 25*60

        await self.set_bot_raceinfo(f"spoiler {preset_name} - {smz3preset.seed.url} - ({smz3preset.seed.code})")
        await self.send_message(smz3preset.seed.url)
        await self.send_message(f"The spoiler log for this race will be sent after the race begins in this room.  A {studytime}s countdown timer at that time will begin.")
        await self.schedule_spoiler_race(spoiler_url, studytime)
        self.seed_rolled = True