"""Data access for the ``triforce_texts`` and ``triforce_texts_config`` tables."""

from typing import Any, Dict, List, Optional

from alttprbot import models


class TriforceTextRepository:
    @staticmethod
    async def create(
        *, pool_name: str, text: str, discord_user_id: int, author: str
    ) -> models.TriforceTexts:
        return await models.TriforceTexts.create(
            pool_name=pool_name, text=text, discord_user_id=discord_user_id, author=author
        )

    @staticmethod
    async def get_by_id(text_id: int) -> Optional[models.TriforceTexts]:
        return await models.TriforceTexts.get_or_none(id=text_id)

    @staticmethod
    async def list_for_pool(
        pool_name: str, extra_filters: Dict[str, Any]
    ) -> List[models.TriforceTexts]:
        """List texts in a pool. ``extra_filters`` is built by the service (not raw input)."""
        return await models.TriforceTexts.filter(pool_name=pool_name, **extra_filters)

    @staticmethod
    async def set_approved(text: models.TriforceTexts, approved: bool) -> None:
        text.approved = approved
        await text.save()

    @staticmethod
    async def list_config_values(pool_name: str, key_name: str) -> List[str]:
        entries = await models.TriforceTextsConfig.filter(pool_name=pool_name, key_name=key_name)
        return [entry.value for entry in entries]
