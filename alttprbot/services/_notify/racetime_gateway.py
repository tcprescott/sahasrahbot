"""RaceTime gateway — the abstraction the service tier uses to reach RaceTime.gg.

The concrete implementation is registered *inward* by the RaceTime presentation
layer (``alttprbot/presentation/racetime/bot.py``) at startup via :func:`register`.
The service tier depends only on this module — never on ``racetime_bot`` or the
live bot singletons.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class RaceTimeGateway(Protocol):
    async def send_message(
        self, room_name: str, message: str, *, direct_to: Optional[str] = None
    ) -> None: ...

    async def set_bot_raceinfo(self, room_name: str, info: str) -> None: ...

    async def invite_user(self, room_name: str, user_id: str) -> None: ...

    async def start_race(self, category: str, **kwargs: Any) -> Any: ...


_impl: Optional[RaceTimeGateway] = None


def register(impl: RaceTimeGateway) -> None:
    """Register the concrete RaceTime gateway (called by the presentation layer)."""
    global _impl
    _impl = impl


def get() -> RaceTimeGateway:
    """Return the registered gateway, or raise if the presentation layer has not started."""
    if _impl is None:
        raise RuntimeError(
            "RaceTime gateway not registered. The RaceTime presentation layer must "
            "call alttprbot.services._notify.racetime_gateway.register() at startup."
        )
    return _impl


def is_registered() -> bool:
    return _impl is not None
