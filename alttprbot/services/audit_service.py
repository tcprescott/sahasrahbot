"""Audit logging service.

Wraps the existing audit tables behind named methods so the rest of the service
tier records audit events without embedding ORM writes. No new generic audit
table is introduced — this composes the existing ``AuditGeneratedGames`` and
``AsyncTournamentAuditLog`` models via their repositories.

Action strings are namespaced ``verb.object`` constants on :class:`AuditActions`;
add a constant when introducing a new action rather than passing a literal.
"""

from typing import Optional

from alttprbot.repositories import (
    AsyncTournamentAuditLogRepository,
    AuditGeneratedGamesRepository,
)


class AuditActions:
    """Namespaced ``verb.object`` audit action constants."""

    GAME_GENERATED = "game.generated"

    ASYNC_RACE_STARTED = "async.race_started"
    ASYNC_RACE_FINISHED = "async.race_finished"
    ASYNC_RACE_FORFEITED = "async.race_forfeited"
    ASYNC_RACE_REVIEWED = "async.race_reviewed"


class AuditService:
    def __init__(self) -> None:
        self.generated_games_repository = AuditGeneratedGamesRepository()
        self.async_log_repository = AsyncTournamentAuditLogRepository()

    async def get_generated_game_by_hash_id(self, hash_id: str):
        """Look up a previously generated game by its hash (for verification)."""
        return await self.generated_games_repository.get_by_hash_id(hash_id)

    async def record_generated_game(
        self,
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
    ):
        """Record a generated seed in the audit log."""
        return await self.generated_games_repository.record(
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

    async def record_async_event(
        self,
        *,
        tournament_id: int,
        action: str,
        actor_id: Optional[int] = None,
        details: Optional[str] = None,
    ):
        """Record an async-tournament audit event. ``actor_id`` is the acting user's id."""
        return await self.async_log_repository.record(
            tournament_id=tournament_id,
            action=action,
            user_id=actor_id,
            details=details,
        )
