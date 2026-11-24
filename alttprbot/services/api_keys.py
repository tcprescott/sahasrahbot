"""Authorization keys that let other tools call SahasrahBot's HTTP API.

This is the only module that reads ``models.AuthorizationKeys`` and
``models.AuthorizationKeyPermissions``. A key grants permissions by ``type`` (such as
``racetimecmd``) and, optionally, ``subtype`` (such as a racetime.gg category slug).
"""

from alttprbot import models


async def can_run_racetime_command(auth_key: str, category: str) -> bool:
    """Whether ``auth_key`` may send chat commands to race rooms in ``category``."""
    access = await models.AuthorizationKeyPermissions.get_or_none(
        auth_key__key=auth_key, type='racetimecmd', subtype=category)
    return access is not None
