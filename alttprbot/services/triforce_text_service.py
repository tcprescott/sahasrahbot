"""Triforce-text submission and moderation service."""

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
