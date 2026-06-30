"""Data access for the ``presets`` table (namespaced user presets)."""

from typing import List, Optional, Tuple

from alttprbot import models


class PresetRepository:
    @staticmethod
    async def get(
        *, namespace_name: str, randomizer: str, preset_name: str
    ) -> Optional[models.Presets]:
        return await models.Presets.get_or_none(
            preset_name=preset_name,
            randomizer=randomizer,
            namespace__name=namespace_name,
        )

    @staticmethod
    async def list_for_namespace(
        *, namespace_name: str, randomizer: Optional[str] = None
    ) -> List[models.Presets]:
        query = models.Presets.filter(namespace__name=namespace_name)
        if randomizer:
            query = query.filter(randomizer=randomizer)
        return await query

    @staticmethod
    async def list_preset_names(*, namespace_name: str, randomizer: str) -> List[str]:
        presets = await models.Presets.filter(
            namespace__name=namespace_name, randomizer=randomizer
        )
        return [preset.preset_name for preset in presets]

    @staticmethod
    async def upsert(
        *,
        namespace: models.PresetNamespaces,
        randomizer: str,
        preset_name: str,
        content: str,
    ) -> Tuple[models.Presets, bool]:
        return await models.Presets.update_or_create(
            randomizer=randomizer,
            preset_name=preset_name,
            namespace=namespace,
            defaults={"content": content},
        )

    @staticmethod
    async def delete_instance(preset: models.Presets) -> None:
        await preset.delete()
