"""Data access for the ``preset_namespaces`` table."""

from typing import List, Optional, Tuple

from tortoise.query_utils import Prefetch

from alttprbot import models


class PresetNamespaceRepository:
    @staticmethod
    async def get_by_name(name: str) -> Optional[models.PresetNamespaces]:
        return await models.PresetNamespaces.get_or_none(name=name)

    @staticmethod
    async def get_by_name_with_collaborators(name: str) -> Optional[models.PresetNamespaces]:
        namespace = await models.PresetNamespaces.get_or_none(name=name)
        if namespace is not None:
            await namespace.fetch_related("collaborators")
        return namespace

    @staticmethod
    async def delete_by_discord_id(discord_user_id: int) -> int:
        return await models.PresetNamespaces.filter(discord_user_id=discord_user_id).delete()

    @staticmethod
    async def get_or_create_by_user(
        *, discord_user_id: int, name: str
    ) -> Tuple[models.PresetNamespaces, bool]:
        return await models.PresetNamespaces.get_or_create(
            discord_user_id=discord_user_id,
            defaults={"name": name},
        )

    @staticmethod
    async def list_all_with_presets_for_randomizer(randomizer: str) -> List[models.PresetNamespaces]:
        return await models.PresetNamespaces.all().prefetch_related(
            Prefetch("presets", queryset=models.Presets.filter(randomizer=randomizer))
        )
