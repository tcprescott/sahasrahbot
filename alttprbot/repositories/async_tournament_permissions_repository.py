"""Data access for the ``async_tournament_permissions`` table."""

from typing import Optional

from alttprbot import models


class AsyncTournamentPermissionsRepository:
    @staticmethod
    async def get_permission(
        tournament: models.AsyncTournament, user: models.Users, role: str
    ) -> Optional[models.AsyncTournamentPermissions]:
        return await models.AsyncTournamentPermissions.get_or_none(
            tournament=tournament, user=user, role=role
        )

    @staticmethod
    async def create_permission(
        tournament: models.AsyncTournament, user: models.Users, role: str
    ) -> models.AsyncTournamentPermissions:
        return await models.AsyncTournamentPermissions.create(
            tournament=tournament, user=user, role=role
        )
