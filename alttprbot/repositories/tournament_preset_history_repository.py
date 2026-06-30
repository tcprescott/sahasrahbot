"""Data access for the ``tournament_preset_history`` table."""

from alttprbot import models


class TournamentPresetHistoryRepository:
    @staticmethod
    async def delete_for_episode(episode_id: int, event_slug: str) -> int:
        return await models.TournamentPresetHistory.filter(
            episode_id=episode_id, event_slug=event_slug
        ).delete()
