"""Triforce-text submission, moderation, selection, and generation service."""

import random
import re
from typing import List, Optional

from alttprbot import models
from alttprbot.repositories import TriforceTextRepository

_TRIFORCE_TEXT_REGEX = re.compile(
    r"^[A-Za-z0-9 ?!,-….~～''↑↓→←あいうえおやゆよかきくけこわをんさしすせそがぎぐたちつてとげござなにぬねのじずぜはひふへほぞだぢまみむめもづでどらりるれろばびぶべぼぱぴぷぺぽゃゅょっぁぃぅぇぉアイウエオヤユヨカキクケコワヲンサシスセソガギグタチツテトゲゴザナニヌネノジズゼハヒフヘホゾダマミムメモヅデドラリルレロバビブベボパピプペポャュョッァィゥェォ]{0,19}$"
)


class TriforceTextService:
    def __init__(self) -> None:
        self.repository = TriforceTextRepository()

    @staticmethod
    def is_valid_line(value: str) -> bool:
        return bool(_TRIFORCE_TEXT_REGEX.match(value))

    async def submit(
        self, *, pool_name: str, lines: List[str], discord_user_id: int, author: str
    ) -> models.TriforceTexts:
        text = "\n".join(lines)
        return await self.repository.create(
            pool_name=pool_name, text=text, discord_user_id=discord_user_id, author=author
        )

    async def get_moderator_ids(self, pool_name: str) -> List[int]:
        return [int(value) for value in await self.repository.list_config_values(pool_name, "moderator")]

    async def is_moderator(self, user_id: int, pool_name: str) -> bool:
        return user_id in await self.get_moderator_ids(pool_name)

    async def list_texts(self, pool_name: str, approved_filter: str) -> List[models.TriforceTexts]:
        extra = {}
        if approved_filter == "true":
            extra["approved"] = True
        elif approved_filter == "false":
            extra["approved"] = False
        elif approved_filter == "pending":
            extra["approved__isnull"] = True
        # any other value => no approval filter (all texts), preserving prior behavior
        return await self.repository.list_for_pool(pool_name, extra)

    async def moderate(self, text_id: int, approve: bool) -> Optional[models.TriforceTexts]:
        text = await self.repository.get_by_id(text_id)
        if text is None:
            return None
        await self.repository.set_approved(text, approve)
        return text

    async def get_balanced_text(self, pool_name: str) -> Optional[str]:
        """Pick an approved triforce text, balanced across submitting users.

        Chooses a random submitter first, then a random text from that submitter,
        so prolific submitters don't dominate the pool.
        """
        discord_user_ids = await self.repository.list_approved_discord_user_ids(pool_name)
        if not discord_user_ids:
            return None

        discord_user_id = random.choice(discord_user_ids)
        triforce_texts = await self.repository.list_approved_for_user(pool_name, discord_user_id)
        return random.choice(triforce_texts).text

    async def get_random_text(self, pool_name: str) -> Optional[str]:
        """Pick a uniformly random approved triforce text from the pool."""
        triforce_texts = await self.repository.list_approved(pool_name)
        if not triforce_texts:
            return None
        return random.choice(triforce_texts).text

    async def generate_with_triforce_text(
        self,
        pool_name: str,
        preset: str,
        settings: dict = None,
        branch: str = "live",
        balanced: bool = True,
    ):
        """Generate an ALTTPR game with a community triforce text injected into the end credits."""
        # Imported lazily to avoid pulling the seed generator into the service-tier
        # import graph at module load (this service is imported from services/__init__).
        from alttprbot.services.seedgen import generator

        data = generator.ALTTPRPreset(preset)
        await data.fetch()
        if balanced:
            text = await self.get_balanced_text(pool_name=pool_name)
        else:
            text = await self.get_random_text(pool_name=pool_name)

        if text:
            data.preset_data['settings']['texts'] = {}
            data.preset_data['settings']['texts']['end_triforce'] = "{NOBORDER}\n" + text

        if settings is not None and isinstance(settings, dict):
            data.preset_data['settings'] = {**data.preset_data['settings'], **settings}

        return await data.generate(allow_quickswap=True, tournament=True, hints=False, spoilers="off", branch=branch)
