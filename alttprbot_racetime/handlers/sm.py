from alttprbot.alttprgen.randomizer.bingosync import BingoSync

from .core import SahasrahBotCoreHandler


class GameHandler(SahasrahBotCoreHandler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bingo = None

    async def ex_bingo(self, args, message):
        self.bingo = await BingoSync.generate(
            room_name="synacktest3",
            passphrase="somethingrandom",
            game_type=4,
            variant_type=4
        )
        await self.send_message(self.bingo.url)

    async def ex_reroll(self, args, message):
        if self.bingo is None:
            await self.send_message("No active bingo game.")

        await self.bingo.new_card(
            game_type=4,
            variant_type=4,
            hide_card='off',
        )
        await self.send_message(self.bingo.url)

    async def status_in_progress(self):
        if self.bingo is None:
            await self.send_message("No active bingo game.")

        await self.bingo.new_card(
            hide_card=False,
            game_type=4,
            variant_type=4,
            custom_json="",
            lockout_mode=1,
            seed="",
        )
        await self.send_message(self.bingo.url)