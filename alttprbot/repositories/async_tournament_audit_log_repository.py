"""Data access for the ``AsyncTournamentAuditLog`` table."""

from typing import Optional

from alttprbot import models


class AsyncTournamentAuditLogRepository:
    @staticmethod
    async def record(
        *,
        tournament_id: int,
        action: str,
        user_id: Optional[int] = None,
        details: Optional[str] = None,
    ) -> models.AsyncTournamentAuditLog:
        return await models.AsyncTournamentAuditLog.create(
            tournament_id=tournament_id,
            user_id=user_id,
            action=action,
            details=details,
        )
