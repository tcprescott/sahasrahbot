"""Data access for RaceTime room state: unlisted rooms + stream-override whitelist."""

from typing import List, Optional, Tuple

from alttprbot import models


class RaceRoomRepository:
    # --- unlisted rooms ---

    @staticmethod
    async def set_unlisted(room_name: str, category: str) -> Tuple[models.RTGGUnlistedRooms, bool]:
        return await models.RTGGUnlistedRooms.update_or_create(
            room_name=room_name, defaults={"category": category}
        )

    @staticmethod
    async def clear_unlisted(room_name: str) -> int:
        return await models.RTGGUnlistedRooms.filter(room_name=room_name).delete()

    @staticmethod
    async def list_unlisted_for_category(category: str) -> List[models.RTGGUnlistedRooms]:
        return await models.RTGGUnlistedRooms.filter(category=category)

    # --- stream-override whitelist ---

    @staticmethod
    async def get_override_whitelist(
        racetime_id: str, category: str
    ) -> Optional[models.RTGGOverrideWhitelist]:
        return await models.RTGGOverrideWhitelist.get_or_none(
            racetime_id=racetime_id, category=category
        )

    # --- watchlist ---

    @staticmethod
    async def list_watchlisted_players(
        entrant_ids: list, category: str
    ) -> List[models.RTGGWatcherPlayer]:
        return await models.RTGGWatcherPlayer.filter(
            racetime_id__in=entrant_ids, rtgg_watcher__category=category
        ).prefetch_related("rtgg_watcher")

    @staticmethod
    async def list_watchers(category: str) -> List[models.RTGGWatcher]:
        return await models.RTGGWatcher.filter(category=category)
