"""Discord gateway — the abstraction the service tier uses to reach Discord.

The concrete implementation is registered *inward* by the Discord presentation
layer (``alttprbot/presentation/discord/bot.py``) at startup via :func:`register`.
The service tier depends only on this module — never on the ``discord`` library
or the live bot singleton — which is what keeps the layering enforceable.

Methods that send messages return awaitables intended to be handed to
``queue.enqueue(...)`` (fire-and-forget). Synchronous resolver methods
(``resolve_channel`` / ``resolve_role`` / ``get_emojis``) are used when a service
genuinely needs presentation-side data, but most flows should keep that in the
presentation layer.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class DiscordGateway(Protocol):
    async def send_channel_message(
        self, channel_id: int, content: Optional[str] = None, *, embed: Any = None
    ) -> None: ...

    async def send_dm(
        self, user_id: int, content: Optional[str] = None, *, embed: Any = None
    ) -> None: ...

    def get_emojis(self) -> list: ...

    def resolve_channel(self, channel_id: int) -> Any: ...

    def resolve_role(self, guild_id: int, role_id: int) -> Any: ...


_impl: Optional[DiscordGateway] = None


def register(impl: DiscordGateway) -> None:
    """Register the concrete Discord gateway (called by the presentation layer)."""
    global _impl
    _impl = impl


def get() -> DiscordGateway:
    """Return the registered gateway, or raise if the presentation layer has not started."""
    if _impl is None:
        raise RuntimeError(
            "Discord gateway not registered. The Discord presentation layer must "
            "call alttprbot.services._notify.discord_gateway.register() at startup."
        )
    return _impl


def is_registered() -> bool:
    return _impl is not None
