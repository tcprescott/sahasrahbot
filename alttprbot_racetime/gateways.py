"""Hands core code (``alttprbot/``) the racetime.gg bots.

``sahasrahbot.py`` calls ``register()`` at startup, so the tournament engine and the
web app can reach the bots through ``alttprbot.services.bots`` without importing
this package.
"""

from alttprbot.services import bots
from alttprbot_racetime.bot import racetime_bots


def register() -> None:
    bots.set_racetime_bots(racetime_bots)
