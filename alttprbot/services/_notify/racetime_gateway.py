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

    async def send_pinned_action(
        self, room_name: str, content: str, *, label: str, help_text: str, message: str
    ) -> None: ...

    async def set_bot_raceinfo(self, room_name: str, info: str) -> None: ...

    async def invite_user(self, room_name: str, user_id: str) -> None: ...

    async def get_entrant_ids(self, room_name: str) -> list: ...

    async def set_invitational(self, room_name: str) -> None: ...

    async def get_entrants(self, room_name: str) -> list: ...

    async def get_started_at(self, room_name: str) -> Optional[str]: ...

    async def edit(self, room_name: str, **kwargs: Any) -> None: ...

    async def schedule_spoiler_race(self, room_name: str, **kwargs: Any) -> Any: ...

    # --- category-level (not tied to a single room) ---
    async def start_race(self, category: str, **kwargs: Any) -> Any: ...

    async def get_team(self, category: str, team_slug: str) -> Any: ...

    async def get_race_status(self, category: str, srl_id: str) -> Optional[str]: ...

    def http_uri(self, category: str, url: str) -> str: ...


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
