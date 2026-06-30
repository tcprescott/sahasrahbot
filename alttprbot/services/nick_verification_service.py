"""Nickname-verification service."""

from alttprbot.repositories import NickVerificationRepository


class NickVerificationService:
    def __init__(self) -> None:
        self.repository = NickVerificationRepository()

    async def delete_for_user(self, discord_user_id: int) -> int:
        """Delete a user's nick-verification records (account-data purge)."""
        return await self.repository.delete_by_discord_id(discord_user_id)
