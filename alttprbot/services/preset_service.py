"""Preset and namespace service (shared by the web API and the seed generator).

Owns the namespace lifecycle and authorization rules for user-managed presets,
delegating all persistence to the preset repositories. Kept free of any web or
Discord types: callers pass plain ids.
"""

import random
import re
from typing import List, Optional

from slugify import slugify
from tortoise.exceptions import DoesNotExist

from alttprbot import models
from alttprbot.repositories import PresetNamespaceRepository, PresetRepository

# Bot maintainer who may manage any namespace (preserved from the original
# generator.is_namespace_owner implementation).
_SUPERUSER_DISCORD_ID = 185198185990324225

_PRESET_NAME_RE = re.compile(r"^[a-zA-Z0-9_]*$")


class PresetService:
    def __init__(self) -> None:
        self.namespaces = PresetNamespaceRepository()
        self.presets = PresetRepository()

    async def create_or_retrieve_namespace(
        self, discord_user_id: int, discord_user_name: str
    ) -> models.PresetNamespaces:
        """Return the caller's namespace, creating one on first use.

        Mirrors the original generator behavior: derive a slug from the display
        name and, on collision, retry once with a random numeric suffix.
        """
        tempnamespaceslug = slugify(discord_user_name, max_length=20)
        try:
            namespace, _ = await self.namespaces.get_or_create_by_user(
                discord_user_id=discord_user_id, name=tempnamespaceslug
            )
        except DoesNotExist:
            tempnamespaceslug = tempnamespaceslug + str(random.randint(0, 99))
            namespace, _ = await self.namespaces.get_or_create_by_user(
                discord_user_id=discord_user_id, name=tempnamespaceslug
            )

        await namespace.fetch_related("collaborators")
        return namespace

    @staticmethod
    def is_namespace_owner(user_id: int, namespace: models.PresetNamespaces) -> bool:
        """Whether ``user_id`` may manage ``namespace``.

        ``namespace.collaborators`` must already be fetched by the caller.
        """
        if namespace.discord_user_id == user_id:
            return True
        if user_id in [collaborator.discord_user_id for collaborator in namespace.collaborators]:
            return True
        if user_id == _SUPERUSER_DISCORD_ID:
            return True
        return False

    @staticmethod
    def is_valid_preset_name(preset_name: str) -> bool:
        return bool(_PRESET_NAME_RE.match(preset_name))

    # --- read/write facade for presentation surfaces ---

    async def get_namespace(self, name: str) -> Optional[models.PresetNamespaces]:
        """Fetch a namespace (with collaborators) by name, or ``None``."""
        return await self.namespaces.get_by_name_with_collaborators(name)

    async def list_presets(
        self, namespace_name: str, randomizer: Optional[str] = None
    ) -> List[models.Presets]:
        return await self.presets.list_for_namespace(
            namespace_name=namespace_name, randomizer=randomizer
        )

    async def get_preset(
        self, namespace_name: str, randomizer: str, preset_name: str
    ) -> Optional[models.Presets]:
        return await self.presets.get(
            namespace_name=namespace_name, randomizer=randomizer, preset_name=preset_name
        )

    async def save_preset(
        self,
        *,
        namespace: models.PresetNamespaces,
        randomizer: str,
        preset_name: str,
        content: str,
    ) -> models.Presets:
        preset, _ = await self.presets.upsert(
            namespace=namespace,
            randomizer=randomizer,
            preset_name=preset_name,
            content=content,
        )
        return preset

    async def delete_preset(self, preset: models.Presets) -> None:
        await self.presets.delete_instance(preset)

    async def list_namespaces_with_presets(self, randomizer: str) -> List[models.PresetNamespaces]:
        return await self.namespaces.list_all_with_presets_for_randomizer(randomizer)

    async def delete_namespaces_for_user(self, discord_user_id: int) -> int:
        """Delete all of a user's preset namespaces (account-data purge)."""
        return await self.namespaces.delete_by_discord_id(discord_user_id)
