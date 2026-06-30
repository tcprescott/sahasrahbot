"""Async-tournament permissions service."""

from typing import Optional

from alttprbot import models
from alttprbot.repositories import AsyncTournamentPermissionsRepository


class AsyncTournamentPermissionsService:
    def __init__(self) -> None:
        self.repository = AsyncTournamentPermissionsRepository()

    async def get_permission(
        self, tournament: models.AsyncTournament, user: models.Users, role: str
    ) -> Optional[models.AsyncTournamentPermissions]:
        return await self.repository.get_permission(tournament, user, role)

    async def create_permission(
        self, tournament: models.AsyncTournament, user: models.Users, role: str
    ) -> models.AsyncTournamentPermissions:
        return await self.repository.create_permission(tournament, user, role)
