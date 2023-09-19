from alttprbot.alttprgen import preset, spoilers, generator
from racetime_bot import monitor_cmd, msg_actions

from .core import SahasrahBotCoreHandler


class GameHandler(SahasrahBotCoreHandler):
    async def status_pending(self):
        await super().status_pending()
        await self.edit(hide_comments=True)

    async def intro(self):
        """
        Send introduction messages.
        """
        if not self.state.get('intro_sent') and not self.tournament:
            await self.send_message(
                f"Hi!  I'm SahasrahBot, your friendly robotic elder and randomizer seed roller! Use {self.command_prefix}help to see what I can do!   Check out https://sahasrahbot.synack.live/rtgg.html for more info.",
                actions=[
                    msg_actions.Action(
                        label='Roll a Game',
                        message="!newrace --preset=${preset} ${--quickswap} ${--spoiler_race} --countdown=${countdown} --branch=${branch}",
                        submit="Roll Game",
                        survey=msg_actions.Survey(
                            msg_actions.TextInput(
                                name='preset',
                                label='Preset',
                                placeholder='eg. standard',
                                help_text='The preset to use for the game.  See https://sahasrahbot.synack.live/rtgg.html for a list of presets.'
                            ),
                            msg_actions.BoolInput(
                                name='--quickswap',
                                label='Quickswap',
                                help_text='Whether or not to allow quickswap.  Defaults to true.',
                                default=True,
                            ),
                            msg_actions.BoolInput(
                                name='--spoiler_race',
                                label='Spoiler Race',
                                help_text='Is this a spoiler race? Default is false.',
                                default=False,
                            ),
                            msg_actions.TextInput(
                                name='countdown',
                                label='Spoiler Countdown (seconds)',
                                placeholder='eg. 900 (ignored if not spoiler race)',
                                help_text='How long to wait before sending the spoiler log.  Defaults to 900 seconds.  Ignored if not a spoiler race.',
                                default='900',
                            ),
                            msg_actions.SelectInput(
                                name='branch',
                                label='Branch',
                                options={
                                    'live': 'Live',
                                    'tournament': 'Tournament',
                                    'beeta': 'Beeta',
                                },
                                help_text='Which branch to use for the game.  Defaults to live.',
                                default='live',
                            ),
                        )
                    )
                ]
            )
            self.state['intro_sent'] = True

    # deprecated
    async def ex_race(self, args, message):
        try:
            preset_name = args[0]
        except IndexError:
            await self.send_message(
                'You must specify a preset!'
            )
            return

        try:
            branch = args[1]
        except IndexError:
            branch = 'live'

        await self.roll_game(preset_name=preset_name, message=message, allow_quickswap=True, branch=branch)

    # async def ex_festive(self, args, message):
    #     try:
    #         preset_name = args[0]
    #     except IndexError:
    #         await self.send_message(
    #             'You must specify a preset!'
    #         )
    #         return
    #     await self.roll_game(preset_name=preset_name, message=message, allow_quickswap=True, endpoint_prefix="/festive")

    # TODO: replace this with !newrace
    async def ex_noqsrace(self, args, message):
        try:
            preset_name = args[0]
        except IndexError:
            await self.send_message(
                'You must specify a preset!'
            )
            return
        try:
            branch = args[1]
        except IndexError:
            branch = 'live'
        await self.roll_game(preset_name=preset_name, message=message, allow_quickswap=False, branch=branch)

    # TODO: delete this in favor of !race
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

    # TODO: delete this in favor of !race
    async def ex_tournamentspoiler(self, args, message):
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
            spoiler = await spoilers.generate_spoiler_game(preset_name, branch='tournament')
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

    # TODO: delete this in favor of !race
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

    async def ex2_newrace(self, message, positional_args, keyword_args):
        if await self.is_locked(message):
            return

        try:
            preset_name = positional_args[1]
        except IndexError:
            preset_name = keyword_args.get('preset', None)

        if not preset_name:
            await self.send_message(
                'You must specify a preset!'
            )
            return

        allow_quickswap = keyword_args.get('quickswap', True)

        try:
            branch = positional_args[2]
        except IndexError:
            branch = keyword_args.get('branch', 'live')

        festive = keyword_args.get('festive', False)
        hints = keyword_args.get('hints', False)

        spoiler_race = keyword_args.get('spoiler_race', False)

        if spoiler_race:
            await self.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")
            try:
                spoiler = await spoilers.generate_spoiler_game(preset_name, branch=branch, allow_quickswap=allow_quickswap, festive=festive)
            except preset.PresetNotFoundException as e:
                await self.send_message(str(e))
                return

            countdown = keyword_args.get('countdown', 900)

            await self.set_bot_raceinfo(f"spoiler {preset_name} - {spoiler.seed.url} - ({'/'.join(spoiler.seed.code)})")
            await self.send_message(spoiler.seed.url)
            await self.send_message(f"The spoiler log for this race will be sent after the race begins in this room.  A {countdown}s countdown timer at that time will begin.")
            await self.schedule_spoiler_race(spoiler.spoiler_log_url, countdown)
        else:
            await self.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")
            try:
                seed = await generator.ALTTPRPreset(preset_name).generate(
                    hints=hints,
                    spoilers="off",
                    tournament=True,
                    allow_quickswap=allow_quickswap,
                    endpoint_prefix="/festive" if festive else "",
                    branch=branch,
                )
            except preset.PresetNotFoundException as e:
                await self.send_message(str(e))
                return

            race_info = f"{preset_name} - {seed.url} - ({'/'.join(seed.code)})"
            await self.set_bot_raceinfo(race_info)
            await self.send_message(seed.url)
            await self.send_message("Seed rolling complete.  See race info for details.")

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

    # deprecated
    async def roll_game(self, preset_name, message, allow_quickswap=True, endpoint_prefix="", branch=None):
        if await self.is_locked(message):
            return

        await self.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")
        try:
            seed = await generator.ALTTPRPreset(preset_name).generate(
                hints=False,
                spoilers="off",
                tournament=True,
                allow_quickswap=allow_quickswap,
                endpoint_prefix=endpoint_prefix,
                branch=branch,
            )
        except preset.PresetNotFoundException as e:
            await self.send_message(str(e))
            return

        race_info = f"{preset_name} - {seed.url} - ({'/'.join(seed.code)})"
        await self.set_bot_raceinfo(race_info)
        await self.send_message(seed.url)
        await self.send_message("Seed rolling complete.  See race info for details.")
        self.seed_rolled = True
