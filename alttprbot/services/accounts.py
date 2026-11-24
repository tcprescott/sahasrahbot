"""What SahasrahBot keeps about a signed-in Discord user, and deleting it on request."""

from alttprbot import models
from alttprbot.services import triforce_texts


async def profile(discord_user_id: int) -> dict:
    user = await models.Users.get_or_none(discord_user_id=discord_user_id)
    namespace = await models.PresetNamespaces.get_or_none(discord_user_id=discord_user_id)
    return {
        'racetime_linked': bool(user and user.rtgg_id),
        'racetime_id': user.rtgg_id if user else None,
        'preset_namespace': namespace.name if namespace else None,
        'moderated_triforce_pools': await triforce_texts.moderated_pools(discord_user_id),
    }


async def purge(discord_user_id: int) -> None:
    """Delete the user's preset namespace (and its presets) and nickname verifications."""
    await models.PresetNamespaces.filter(discord_user_id=discord_user_id).delete()
    await models.NickVerification.filter(discord_user_id=discord_user_id).delete()
