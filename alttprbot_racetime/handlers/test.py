from .sm import GameHandler as SMGameHandler

class GameHandler(SMGameHandler):
    async def status_invitational(self):
        await self.send_message("switched to invitational status")

    async def status_open(self):
        await self.send_message("switched to open status")

    async def status_in_progress(self):
        await self.send_message("switched to in progress status")