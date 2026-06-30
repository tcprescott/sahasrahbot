"""Verified-racer service: records a racer's verification status against a config."""

import datetime
from typing import Tuple

from alttprbot import models
from alttprbot.repositories import VerifiedRacerRepository


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class VerifiedRacerService:
    def __init__(self) -> None:
        self.repository = VerifiedRacerRepository()

    async def record_verification(
        self,
        user: models.Users,
        racer_verification: models.RacerVerification,
        estimated_count: int,
    ) -> models.VerifiedRacer:
        """Create or refresh a user's verification record for this config."""
        racer = await self.repository.get_for_user_and_verification(user, racer_verification)
        if racer is None:
            return await self.repository.create(
                user=user,
                racer_verification=racer_verification,
                last_verified=_now(),
                estimated_count=estimated_count,
            )
        await self.repository.update_verification(
            racer, last_verified=_now(), estimated_count=estimated_count
        )
        return racer

    async def get_or_create_for_user(
        self, user: models.Users, racer_verification: models.RacerVerification
    ) -> Tuple[models.VerifiedRacer, bool]:
        return await self.repository.get_or_create_for_user(user, racer_verification)

    async def mark_verified(
        self, verified_racer: models.VerifiedRacer, estimated_count: int
    ) -> None:
        await self.repository.update_verification(
            verified_racer, last_verified=_now(), estimated_count=estimated_count
        )

    async def revoke(self, verified_racer: models.VerifiedRacer) -> None:
        await self.repository.delete_instance(verified_racer)
