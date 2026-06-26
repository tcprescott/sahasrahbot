"""User account service: lookups, RaceTime account linking and merges."""

from typing import Optional

from alttprbot import models
from alttprbot.repositories import UserRepository


class UserService:
    def __init__(self) -> None:
        self.repository = UserRepository()

    async def get_by_discord_id(self, discord_user_id: int) -> Optional[models.Users]:
        return await self.repository.get_by_discord_id(discord_user_id)

    async def get_by_id(self, user_id: int) -> Optional[models.Users]:
        return await self.repository.get_by_id(user_id)

    async def get_by_rtgg_id(self, rtgg_id: str) -> Optional[models.Users]:
        return await self.repository.get_by_rtgg_id(rtgg_id)

    async def get_or_create_by_discord_id(
        self, discord_user_id: int, *, display_name: Optional[str] = None
    ) -> models.Users:
        user, _ = await self.repository.get_or_create_by_discord_id(
            discord_user_id, display_name=display_name
        )
        return user

    async def link_racetime_account(
        self, *, discord_user_id: int, display_name: str, rtgg_id: str, access_token: str
    ) -> None:
        """Link a verified RaceTime identity to a Discord user.

        Three cases, preserved from the original verification flow:
        - both a rtgg-keyed and a discord-keyed user exist and differ -> merge them;
        - no rtgg-keyed user -> upsert keyed on the discord id;
        - otherwise -> upsert keyed on the rtgg id.
        """
        rtgg_user = await self.repository.get_by_rtgg_id(rtgg_id)
        discord_user = await self.repository.get_by_discord_id(discord_user_id)

        if rtgg_user != discord_user and rtgg_user is not None and discord_user is not None:
            kept_user = await self.repository.merge(rtgg_user, discord_user)
            kept_user.display_name = display_name
            await kept_user.save()
        elif rtgg_user is None:
            await self.repository.upsert_by_discord_id(
                discord_user_id,
                {"rtgg_id": rtgg_id, "rtgg_access_token": access_token, "display_name": display_name},
            )
        else:
            await self.repository.upsert_by_rtgg_id(
                rtgg_id,
                {"discord_user_id": discord_user_id, "rtgg_access_token": access_token, "display_name": display_name},
            )
