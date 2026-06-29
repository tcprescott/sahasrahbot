"""Concrete RaceTime gateway — the presentation-side implementation of
``alttprbot.services._notify.racetime_gateway.RaceTimeGateway``.

Wraps the per-category ``racetime_bots`` dict. Category-level calls
(``start_race`` / ``get_team`` / ``http_uri``) go to the category bot; room-level
calls resolve the live handler for a room via ``compat.get_room_handler`` (searching
across categories, since room names are globally unique on RaceTime). Registered
inward at startup; resolution is lazy.
"""

from __future__ import annotations

from typing import Any, Optional

from racetime_bot import msg_actions

from alttprbot.presentation.racetime.compat import get_room_handler
from alttprbot.services._notify import racetime_gateway


class RaceTimeGatewayImpl:
    def __init__(self, bots: dict) -> None:
        self.bots = bots

    def _handler(self, room_name: str):
        for bot in self.bots.values():
            handler = get_room_handler(bot, room_name)
            if handler is not None:
                return handler
        return None

    # --- room-level ---
    async def send_message(
        self, room_name: str, message: str, *, direct_to: Optional[str] = None
    ) -> None:
        handler = self._handler(room_name)
        if handler is None:
            return
        if direct_to is not None:
            await handler.send_message(message, direct_to=direct_to)
        else:
            await handler.send_message(message)

    async def set_bot_raceinfo(self, room_name: str, info: str) -> None:
        handler = self._handler(room_name)
        if handler is not None:
            await handler.set_bot_raceinfo(info)

    async def send_pinned_action(
        self, room_name: str, content: str, *, label: str, help_text: str, message: str
    ) -> None:
        """Post a pinned chat message carrying a single action button.

        Mirrors the legacy ``send_room_welcome`` "Tournament Controls:" pinned
        ``msg_actions.Action`` (the "Roll Tournament Seed" button).
        """
        handler = self._handler(room_name)
        if handler is None:
            return
        await handler.send_message(
            content,
            actions=[msg_actions.Action(label=label, help_text=help_text, message=message)],
            pinned=True,
        )

    async def invite_user(self, room_name: str, user_id: str) -> None:
        handler = self._handler(room_name)
        if handler is not None:
            await handler.invite_user(user_id)

    async def get_entrant_ids(self, room_name: str) -> list:
        """The live entrant user-ids for a room (full list, no status filter).

        Mirrors the legacy ``self.rtgg_handler.data['entrants']`` read: the handler's
        ``data`` dict is reassigned on every ``race.data`` websocket frame, so this
        returns the entrant set as it exists *at call time* (used for the post-roll
        seed-URL whisper, which must see late joiners / dropped entrants).
        """
        handler = self._handler(room_name)
        if handler is None:
            return []
        return [e["user"]["id"] for e in handler.data.get("entrants", [])]

    async def get_entrants(self, room_name: str) -> list:
        """Neutral entrant records (id / name / twitch_name) for a room, read at call time.

        Mirrors the legacy ``race_room_data['entrants']`` iteration in
        ``write_eligible_async_entrants`` — flattened to the fields the service tier needs
        so it never touches the raw RaceTime entrant shape.
        """
        handler = self._handler(room_name)
        if handler is None:
            return []
        return [
            {
                "id": e["user"]["id"],
                "name": e["user"]["name"],
                "twitch_name": e["user"].get("twitch_name", None),
            }
            for e in handler.data.get("entrants", [])
        ]

    async def get_started_at(self, room_name: str):
        handler = self._handler(room_name)
        if handler is None:
            return None
        return handler.data.get("started_at")

    async def set_invitational(self, room_name: str) -> None:
        handler = self._handler(room_name)
        if handler is not None:
            await handler.set_invitational()

    async def edit(self, room_name: str, **kwargs: Any) -> None:
        handler = self._handler(room_name)
        if handler is not None:
            await handler.edit(**kwargs)

    async def schedule_spoiler_race(self, room_name: str, **kwargs: Any) -> Any:
        handler = self._handler(room_name)
        if handler is None:
            return None
        return await handler.schedule_spoiler_race(**kwargs)

    # --- category-level ---
    async def start_race(self, category: str, **kwargs: Any) -> Any:
        return await self.bots[category].startrace(**kwargs)

    async def get_team(self, category: str, team_slug: str) -> Any:
        return await self.bots[category].get_team(team_slug)

    def http_uri(self, category: str, url: str) -> str:
        return self.bots[category].http_uri(url)


def register(bots: dict) -> None:
    racetime_gateway.register(RaceTimeGatewayImpl(bots))
