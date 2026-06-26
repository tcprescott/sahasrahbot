"""Data access for the ``verified_racer`` table."""

from datetime import datetime
from typing import Optional, Tuple

from alttprbot import models


class VerifiedRacerRepository:
    @staticmethod
    async def get_for_user_and_verification(
        user: models.Users, racer_verification: models.RacerVerification
    ) -> Optional[models.VerifiedRacer]:
        return await models.VerifiedRacer.get_or_none(
            user=user, racer_verification=racer_verification
        )

    @staticmethod
    async def create(
        *,
        user: models.Users,
        racer_verification: models.RacerVerification,
        last_verified: datetime,
        estimated_count: int,
    ) -> models.VerifiedRacer:
        return await models.VerifiedRacer.create(
            user=user,
            racer_verification=racer_verification,
            last_verified=last_verified,
            estimated_count=estimated_count,
        )

    @staticmethod
    async def get_or_create_for_user(
        user: models.Users, racer_verification: models.RacerVerification
    ) -> Tuple[models.VerifiedRacer, bool]:
        return await models.VerifiedRacer.get_or_create(
            user=user, defaults={"racer_verification": racer_verification}
        )

    @staticmethod
    async def update_verification(
        verified_racer: models.VerifiedRacer, *, last_verified: datetime, estimated_count: int
    ) -> None:
        verified_racer.last_verified = last_verified
        verified_racer.estimated_count = estimated_count
        await verified_racer.save()

    @staticmethod
    async def delete_instance(verified_racer: models.VerifiedRacer) -> None:
        await verified_racer.delete()
