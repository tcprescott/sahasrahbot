from .core import SahasrahBotCoreHandler


class GameHandler(SahasrahBotCoreHandler):
    async def intro(self):
        pass  # no-op: this category posts no intro message

    async def ex_help(self, args, message):
        pass  # no-op: command intentionally disabled for this category

    async def ex_lock(self, args, message):
        pass  # no-op: command intentionally disabled for this category

    async def ex_unlock(self, args, message):
        pass  # no-op: command intentionally disabled for this category

    async def ex_cancel(self, args, message):
        pass  # no-op: command intentionally disabled for this category

    async def ex_tournamentrace(self, args, message):
        pass  # no-op: command intentionally disabled for this category
