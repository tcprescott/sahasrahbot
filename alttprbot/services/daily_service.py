"""Daily challenge service.

Owns the "have we already recorded today's daily?" decision: validate the hash,
check the repository, and record a new daily exactly once. Returns whether the
hash was newly recorded so the presentation layer knows when to announce it.
"""

import logging

from alttprbot.repositories import DailyRepository

logger = logging.getLogger(__name__)


class DailyService:
    def __init__(self) -> None:
        self.daily_repository = DailyRepository()

    async def record_if_new(self, hash_id: str) -> bool:
        """Record ``hash_id`` as the current daily if it has not been seen.

        Returns ``True`` when the hash was newly recorded (the caller should
        announce it) and ``False`` when it was already known. Raises
        ``ValueError`` when ``hash_id`` is empty.
        """
        if not hash_id:
            raise ValueError("hash_id is required")

        if await self.daily_repository.exists_by_hash(hash_id):
            return False

        logger.info("Detected new daily hash %s", hash_id)
        await self.daily_repository.create(hash_id)
        return True
