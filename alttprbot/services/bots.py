"""Where core code gets the running Discord client and racetime.gg bots from.

Core (``alttprbot/``) must not import a front end, but the tournament engine and
the web app still need the live bots: the engine resolves its guild and channels
and starts race rooms, the web app checks the Discord connection and looks up
guilds. The front ends register their singletons here at startup:
``alttprbot_discord.gateways.register()`` sets the Discord client and
``alttprbot_racetime.gateways.register()`` sets the racetime bots, both called from
``sahasrahbot.py`` (and from ``devserver/bootstrap.py`` for the dev server).

Callers look the bots up when they use them, never at import time, so whatever is
registered at that moment (a fake in tests or the dev server) is what they get.
"""

from typing import Any, Dict, Optional

_discord_client = None
_racetime_bots: Optional[Dict[str, Any]] = None


def set_discord_client(client) -> None:
    """Register the Discord client (a ``discord.Client``) core code should use."""
    global _discord_client
    _discord_client = client


def discord():
    """The registered Discord client. Raises RuntimeError if none is registered."""
    if _discord_client is None:
        raise RuntimeError(
            "No Discord client registered; call alttprbot_discord.gateways.register() at startup."
        )
    return _discord_client


def set_racetime_bots(bots: Dict[str, Any]) -> None:
    """Register the racetime.gg bots, keyed by category slug.

    The mapping is kept by reference, so bots added to it later are visible too.
    """
    global _racetime_bots
    _racetime_bots = bots


def racetime_bots() -> Dict[str, Any]:
    """The registered racetime.gg bots, keyed by category slug.

    Raises RuntimeError if none are registered.
    """
    if _racetime_bots is None:
        raise RuntimeError(
            "No racetime bots registered; call alttprbot_racetime.gateways.register() at startup."
        )
    return _racetime_bots


def racetime_bot(category: str):
    """The racetime.gg bot for ``category``. Raises KeyError for an unknown category."""
    return racetime_bots()[category]
