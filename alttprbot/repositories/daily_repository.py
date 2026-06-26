"""Data access for the ``daily`` table."""

from alttprbot import models


class DailyRepository:
    @staticmethod
    async def exists_by_hash(hash_id: str) -> bool:
        """Return whether a daily row already exists for ``hash_id``."""
        return await models.Daily.filter(hash=hash_id).exists()

    @staticmethod
    async def create(hash_id: str) -> models.Daily:
        """Persist a new daily row for ``hash_id``."""
        return await models.Daily.create(hash=hash_id)
