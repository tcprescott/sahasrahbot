"""User account service: lookups, RaceTime account linking and merges."""

import logging
from typing import Optional

from tortoise.exceptions import IntegrityError

from alttprbot import models
from alttprbot.repositories import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self) -> None:
        self.repository = UserRepository()

    async def get_by_discord_id(self, discord_user_id: int) -> Optional[models.Users]:
        return await self.repository.get_by_discord_id(discord_user_id)

    async def get_by_id(self, user_id: int) -> Optional[models.Users]:
        return await self.repository.get_by_id(user_id)

    async def get_by_rtgg_id(self, rtgg_id: str) -> Optional[models.Users]:
        return await self.repository.get_by_rtgg_id(rtgg_id)

    async def list_users_without_display_name(self) -> "list[models.Users]":
        return await self.repository.list_without_display_name()

    @staticmethod
    def _validate_display_name(display_name) -> str:
        if not isinstance(display_name, str):
            raise ValueError("Display name must be text.")
        display_name = display_name.strip()
        if not 1 <= len(display_name) <= 32:
            raise ValueError("Display name must be between 1 and 32 characters.")
        return display_name

    async def update_display_name(self, user: models.Users, display_name: str) -> None:
        display_name = self._validate_display_name(display_name)

        try:
            await self.repository.set_display_name(user, display_name)
        except IntegrityError as exc:
            raise ValueError("That display name is already taken.") from exc

    async def set_own_display_name(self, discord_user_id: int, display_name: str) -> str:
        """Validate and persist a user-chosen display name, creating the user row if needed.

        Validates before touching the database so an invalid name from a brand-new
        visitor doesn't leave behind a junk ``Users`` row.
        """
        display_name = self._validate_display_name(display_name)
        user = await self.get_or_create_by_discord_id(discord_user_id)
        await self.update_display_name(user, display_name)
        return user.display_name

    async def get_account_summary(self, discord_user_id: int) -> dict:
        """Linked-account state for the profile page, keyed by provider."""
        user = await self.repository.get_by_discord_id(discord_user_id)
        return {
            "display_name": user.display_name if user else None,
            "racetime": {
                "linked": bool(user and user.rtgg_id),
                "id": user.rtgg_id if user else None,
                "url": user.racetime_profile if user else None,
            },
            "twitch": {
                "linked": bool(user and user.twitch_name),
                "name": user.twitch_name if user else None,
            },
        }

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

        The Discord username is only a *fallback* display name: it's applied when
        the user doesn't already have one, but never overwrites a name the user
        chose for themselves via the profile page.
        """
        rtgg_user = await self.repository.get_by_rtgg_id(rtgg_id)
        discord_user = await self.repository.get_by_discord_id(discord_user_id)

        if rtgg_user != discord_user and rtgg_user is not None and discord_user is not None:
            kept_user = await self.repository.merge(rtgg_user, discord_user)
            if not kept_user.display_name:
                kept_user.display_name = display_name
                try:
                    await kept_user.save()
                except IntegrityError:
                    logger.warning(
                        "Skipped fallback display name %r after RaceTime merge: name already taken.",
                        display_name,
                    )
        elif rtgg_user is None:
            defaults = {"rtgg_id": rtgg_id, "rtgg_access_token": access_token}
            if discord_user is None or not discord_user.display_name:
                defaults["display_name"] = display_name
            await self.repository.upsert_by_discord_id(discord_user_id, defaults)
        else:
            defaults = {"discord_user_id": discord_user_id, "rtgg_access_token": access_token}
            if not rtgg_user.display_name:
                defaults["display_name"] = display_name
            await self.repository.upsert_by_rtgg_id(rtgg_id, defaults)

    async def unlink_racetime_account(self, discord_user_id: int) -> None:
        """Clear a user's linked RaceTime.gg identity (local link only, no upstream revoke)."""
        user = await self.repository.get_by_discord_id(discord_user_id)
        if user is None or user.rtgg_id is None:
            raise ValueError("No RaceTime.gg account is linked.")

        await self.repository.clear_racetime_link(user)
