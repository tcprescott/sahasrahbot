from alttprbot.alttprgen.randomizer.bingosync import BingoSync

from .core import SahasrahBotCoreHandler


class GameHandler(SahasrahBotCoreHandler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bingo = None
