import asyncio
from .smr import GameHandler as TestGameHandler


class GameHandler(TestGameHandler):
    async def ex_test(self, args, message):
        try:
            seconds = int(args[0])
        except IndexError:
            seconds = 30
        except ValueError:
            await self.send_message("Invalid number of seconds")
            return
        await self.send_message(f"initated test command, waiting {seconds} seconds")
        await self.countdown_timer(seconds)
        await self.send_message("test command complete")
