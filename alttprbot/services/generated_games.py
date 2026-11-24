"""The audit log of seeds SahasrahBot generated (``models.AuditGeneratedGames``).

Seed generation (``alttprbot/alttprgen/generator.py``) writes it; this module answers
questions about it.
"""

from typing import Optional

from alttprbot import models


async def find_by_hash(hash_id: str) -> Optional[models.AuditGeneratedGames]:
    """The audit row for a game hash, or None if SahasrahBot didn't generate it."""
    return await models.AuditGeneratedGames.get_or_none(hash_id=hash_id)
