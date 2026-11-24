"""Hands core code (``alttprbot/``) the racetime.gg bots.

``sahasrahbot.py`` calls ``register()`` at startup, so the tournament engine and the
web app can reach the bots through ``alttprbot.services.bots`` without importing
this package.
"""

from alttprbot.observability import runtime
from alttprbot.services import bots
from alttprbot_racetime.bot import racetime_bots


def register() -> None:
    bots.set_racetime_bots(racetime_bots)
    # Rooms each bot is in, for the Sentry metrics sampler.
    runtime.add_source('racetime', rooms_source)


def rooms_source():
    return [('racetime.rooms', len(getattr(bot, 'handlers', {})), {'category': slug})
            for slug, bot in racetime_bots.items()]
