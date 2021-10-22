import random

from alttprbot.alttprgen import preset, smz3multi, smvaria
from alttprbot.alttprgen.randomizer import smdash
from pyz3r.exceptions import UnableToGenerate, UnableToRetrieve

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

        if self.data.get('team_race', False) is False:
            await self.send_message('This must be a team race.')
            return

        if not self.is_equal_teams:
            await self.send_message("Teams are unequal in size.")
            return

        await self.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")

        seed_number = random.randint(0, 2147483647)

        try:
            teams = self.teams
            for team in teams:
                seed = await smz3multi.generate_multiworld(preset_name, teams[team], tournament=True, randomizer='sm', seed_number=seed_number)
                await self.send_message(f"Team {team}: {seed.url}")
                await self.send_message("------")
        except Exception as e:
            await self.send_message(str(e))
            return

        race_info = f"SM Multiworld - {preset_name}"
        await self.set_raceinfo(race_info)
        await self.send_message("Seed rolling complete.")
        self.seed_rolled = True

    async def ex_smleagueplayoff(self, args, message):
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

        try:
            seed = await smvaria.generate_league_playoff(args[0], args[1], args[2])
        except Exception as e:
            await self.send_message(str(e))
            return

        race_info = f"Super Metroid League Playoffs - {preset_name} - {seed.url} - {', '.join(args)}"
        await self.set_raceinfo(race_info)
        await self.send_message(seed.url)
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True

    async def ex_total(self, args, message):
        self.ex_totalrace(args, message)

    async def ex_totalrace(self, args, message):
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
        try:
            seed, _ = await preset.get_preset(preset_name, randomizer='sm', spoilers="off")
        except preset.PresetNotFoundException as e:
            await self.send_message(str(e))
            return

        race_info = f"SM Total Randomizer - {preset_name} - {seed.url} - ({seed.code})"
        await self.set_raceinfo(race_info)
        await self.send_message(seed.url)
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True

    async def ex_smvaria(self, args, message):
        await self.ex_variarace(args, message)

    async def ex_varia(self, args, message):
        await self.ex_variarace(args, message)

    async def ex_variarace(self, args, message):
        if await self.is_locked(message):
            return

        try:
            settings = args[0],
            skills = args[1]
        except IndexError:
            await self.send_message(
                'You must specify setting and skill presets!'
            )
            return

        await self.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")
        try:
            seed = await smvaria.generate_preset(
                settings=settings,
                skills=skills,
                race=True
            )
        except (UnableToRetrieve, UnableToGenerate) as e:
            await self.send_message(str(e))
            return

        await self.set_raceinfo(f"SM VARIA Randomizer - {settings} / {skills} - {seed.url}")
        await self.send_message(seed.url)
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True

    async def ex_smdash(self, args, message):
        await self.ex_dashrace(args, message)

    async def ex_dash(self, args, message):
        await self.ex_dashrace(args, message)

    async def ex_dashrace(self, args, message):
        if await self.is_locked(message):
            return

        await self.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")
        try:
            url = await smdash.create_smdash(mode=args[0])
        except Exception as e:
            await self.send_message(str(e))
            return

        await self.set_raceinfo(f"SM Dash Randomizer - {url}")
        await self.send_message(f"{url}")
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!total <preset>, !varia <settings> <skills>, !dash <mode>, !multiworld <preset>\" to generate a seed.  Check out https://sahasrahbot.synack.live/rtgg.html for more info.")
