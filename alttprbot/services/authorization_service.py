"""Authorization-key service for API-key gated actions."""

from alttprbot.repositories import AuthorizationKeyRepository


class AuthorizationService:
    def __init__(self) -> None:
        self.repository = AuthorizationKeyRepository()

    async def is_racetime_cmd_authorized(self, auth_key: str, category: str) -> bool:
        permission = await self.repository.get_permission(auth_key, "racetimecmd", category)
        return permission is not None
