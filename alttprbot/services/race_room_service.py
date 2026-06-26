"""RaceTime room-state service: unlisted-room tracking + stream-override whitelist."""

from typing import List, Optional

from alttprbot import models
from alttprbot.repositories import RaceRoomRepository


class RaceRoomService:
    def __init__(self) -> None:
        self.repository = RaceRoomRepository()

    async def set_unlisted(self, room_name: str, category: str) -> None:
        await self.repository.set_unlisted(room_name, category)

    async def clear_unlisted(self, room_name: str) -> None:
        await self.repository.clear_unlisted(room_name)

    async def list_unlisted_for_category(self, category: str) -> List[models.RTGGUnlistedRooms]:
        return await self.repository.list_unlisted_for_category(category)

    async def get_override_whitelist(
        self, racetime_id: str, category: str
    ) -> Optional[models.RTGGOverrideWhitelist]:
        """Return the stream-override whitelist row (with ``expires``), or ``None``."""
        return await self.repository.get_override_whitelist(racetime_id, category)
