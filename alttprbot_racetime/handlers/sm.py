import random

from .core import SahasrahBotCoreHandler


class GameHandler(SahasrahBotCoreHandler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.roll_bingo_on_start = False

    async def ex_bingo(self, args, message):
        self.roll_bingo_on_start = True
        await self.send_message("Bingo card will be rolled at race start!")

    async def status_in_progress(self):
        if self.tournament:
            await self.tournament.on_race_start()

        if self.roll_bingo_on_start:
            bingoseed = random.randint(0, 899999)
            await self.send_message(f"-----------------------")
            await self.send_message(f"https://www.speedrunslive.com/tools/supermetroid-bingo/?seed={bingoseed}")
            await self.send_message(f"-----------------------")
