from alttprbot.alttprgen import preset, spoilers, generator
from racetime_bot import monitor_cmd

from .core import SahasrahBotCoreHandler


class GameHandler(SahasrahBotCoreHandler):
    async def status_pending(self):
        await super().status_pending()
        await self.edit(hide_comments=True)

    async def ex_race(self, args, message):
        try:
            preset_name = args[0]
        except IndexError:
            await self.send_message(
                'You must specify a preset!'
            )
            return
        await self.roll_game(preset_name=preset_name, message=message, allow_quickswap=True)

    async def ex_festive(self, args, message):
        try:
            preset_name = args[0]
        except IndexError:
            await self.send_message(
                'You must specify a preset!'
            )
            return
        await self.roll_game(preset_name=preset_name, message=message, allow_quickswap=True, endpoint_prefix="/festive")

    async def ex_noqsrace(self, args, message):
        try:
            preset_name = args[0]
        except IndexError:
            await self.send_message(
                'You must specify a preset!'
            )
            return
        await self.roll_game(preset_name=preset_name, message=message, allow_quickswap=False)

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
        try:
            spoiler = await spoilers.generate_spoiler_game(preset_name)
        except preset.PresetNotFoundException as e:
            await self.send_message(str(e))
            return

        try:
            studytime = int(args[1])
        except IndexError:
            studytime = spoiler.preset.preset_data.get('studytime', 900)

        await self.set_bot_raceinfo(f"spoiler {preset_name} - {spoiler.seed.url} - ({'/'.join(spoiler.seed.code)})")
        await self.send_message(spoiler.seed.url)
        await self.send_message(f"The spoiler log for this race will be sent after the race begins in this room.  A {studytime}s countdown timer at that time will begin.")
        await self.schedule_spoiler_race(spoiler.spoiler_log_url, studytime)
        self.seed_rolled = True

    async def ex_progression(self, args, message):
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
            spoiler = await spoilers.generate_spoiler_game(preset_name, spoiler_type='progression')
        except preset.PresetNotFoundException as e:
            await self.send_message(str(e))
            return

        await self.set_bot_raceinfo(f"spoiler {preset_name} - {spoiler.seed.url} - ({'/'.join(spoiler.seed.code)})")
        await self.send_message(spoiler.seed.url)
        await self.send_message("The progression spoiler for this race will be sent after the race begins in this room.")
        await self.schedule_spoiler_race(spoiler.spoiler_log_url, 0)
        self.seed_rolled = True

    async def ex_mystery(self, args, message):
        if await self.is_locked(message):
            return

        weightset = args[0] if args else 'weighted'

        await self.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")
        try:
            mystery = await generator.ALTTPRMystery(weightset).generate(tournament=True, spoilers="mystery")
            seed = mystery.seed
        except generator.WeightsetNotFoundException as e:
            await self.send_message(str(e))
            return

        if mystery.custom_instructions:
            await self.send_message(f"Instructions: {mystery.custom_instructions}")
            await self.set_bot_raceinfo(f"Instructions: {mystery.custom_instructions} - mystery {weightset} - {seed.url} - ({'/'.join(seed.code)})")
        else:
            await self.set_bot_raceinfo(f"mystery {weightset} - {seed.url} - ({'/'.join(seed.code)})")

        await self.send_message(seed.url)
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True

    # TODO: refactor this pile of shit
    @monitor_cmd
    async def ex_cancel(self, args, message):
        self.seed_rolled = False
        await self.set_bot_raceinfo("New Race")
        # await tournament_results.delete_active_tournament_race(self.data.get('name'))
        await self.delete_spoiler_race()
        await self.send_message("Reseting bot state.  You may now roll a new game.")

    async def ex_help(self, args, message):
        await self.send_message("Available commands:\n\"!race <preset>\" to generate a race preset.\n\"!mystery <weightset>\" to generate a mystery game.\n\"!spoiler <preset>\" to generate a spoiler race.  Check out https://sahasrahbot.synack.live/rtgg.html for more info.")

    async def ex_register(self, args, message):
        await self.send_message("Lazy Kid ain't got nothing compared to me.")

    async def ex_vt(self, args, message):
        await self.send_message("You summon Veetorp, he looks around confused and curses your next game with bad (CS)PRNG.")

    async def ex_synack(self, args, message):
        await self.send_message("You need to be more creative.")

    async def roll_game(self, preset_name, message, allow_quickswap=True, endpoint_prefix=""):
        if await self.is_locked(message):
            return

        await self.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")
        try:
            seed = await generator.ALTTPRPreset(preset_name).generate(
                hints=False,
                spoilers="off",
                tournament=True,
                allow_quickswap=allow_quickswap,
                endpoint_prefix=endpoint_prefix
            )
        except preset.PresetNotFoundException as e:
            await self.send_message(str(e))
            return

        race_info = f"{preset_name} - {seed.url} - ({'/'.join(seed.code)})"
        await self.set_bot_raceinfo(race_info)
        await self.send_message(seed.url)
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True
