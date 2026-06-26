"""Data access for the ``audit_generated_games`` table."""

from typing import Optional

from alttprbot import models


class AuditGeneratedGamesRepository:
    @staticmethod
    async def record(
        *,
        randomizer: Optional[str],
        hash_id: Optional[str],
        permalink: Optional[str],
        settings: Optional[dict],
        gentype: Optional[str],
        genoption: Optional[str],
        customizer: int = 0,
        doors: bool = False,
        avianart: bool = False,
    ) -> models.AuditGeneratedGames:
        return await models.AuditGeneratedGames.create(
            randomizer=randomizer,
            hash_id=hash_id,
            permalink=permalink,
            settings=settings,
            gentype=gentype,
            genoption=genoption,
            customizer=customizer,
            doors=doors,
            avianart=avianart,
        )
