"""Data access for the ``authorization_key_permissions`` table."""

from typing import Optional

from alttprbot import models


class AuthorizationKeyRepository:
    @staticmethod
    async def get_permission(
        auth_key: str, permission_type: str, subtype: Optional[str]
    ) -> Optional[models.AuthorizationKeyPermissions]:
        return await models.AuthorizationKeyPermissions.get_or_none(
            auth_key__key=auth_key, type=permission_type, subtype=subtype
        )

    @staticmethod
    async def get_by_type(
        auth_key: str, permission_type: str
    ) -> Optional[models.AuthorizationKeyPermissions]:
        """Match any permission of ``permission_type`` regardless of subtype."""
        return await models.AuthorizationKeyPermissions.get_or_none(
            auth_key__key=auth_key, type=permission_type
        )
