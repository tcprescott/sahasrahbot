"""Authorization-key service for API-key gated actions."""

from alttprbot.repositories import AuthorizationKeyRepository


class AuthorizationService:
    def __init__(self) -> None:
        self.repository = AuthorizationKeyRepository()

    async def is_racetime_cmd_authorized(self, auth_key: str, category: str) -> bool:
        permission = await self.repository.get_permission(auth_key, "racetimecmd", category)
        return permission is not None

    async def is_api_authorized(self, auth_key: str, permission_type: str) -> bool:
        """Whether ``auth_key`` grants ``permission_type`` (any subtype)."""
        permission = await self.repository.get_by_type(auth_key, permission_type)
        return permission is not None
