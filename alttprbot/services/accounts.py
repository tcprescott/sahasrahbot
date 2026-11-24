"""What SahasrahBot keeps about a Discord user: their profile, the racetime.gg account
linked to it, and deleting it on request."""

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


async def link_racetime(discord_user_id: int, discord_name: str, rtgg_id: str, rtgg_access_token: str) -> None:
    """Record that this Discord user signed in to racetime.gg as ``rtgg_id``.

    When the racetime.gg account and the Discord account already have a ``Users`` row
    each, the two rows are merged into the racetime.gg one (see ``merge_users``). The
    merge keeps that row's stored access token, as the link has always done.
    """
    rtgg_user = await models.Users.get_or_none(rtgg_id=rtgg_id)
    discord_user = await models.Users.get_or_none(discord_user_id=discord_user_id)
    if rtgg_user != discord_user and rtgg_user is not None and discord_user is not None:
        kept_user = await merge_users(rtgg_user, discord_user)
        kept_user.display_name = discord_name
        await kept_user.save()
    elif rtgg_user is None:
        await models.Users.update_or_create(discord_user_id=discord_user_id,
                                            defaults={'rtgg_id': rtgg_id, 'rtgg_access_token': rtgg_access_token,
                                                      'display_name': discord_name})
    else:
        await models.Users.update_or_create(rtgg_id=rtgg_id,
                                            defaults={'discord_user_id': discord_user_id,
                                                      'rtgg_access_token': rtgg_access_token,
                                                      'display_name': discord_name})


async def merge_users(user_to_keep: models.Users, victim: models.Users) -> models.Users:
    """Fold ``victim`` into ``user_to_keep``: copy its Discord and racetime.gg ids, point
    the rows that name it at the kept user, then delete it.

    The async tournament feature is gone, but its tables (and their rows) are kept, so
    their user references are still rewritten here.
    """
    if victim.discord_user_id:
        user_to_keep.discord_user_id = victim.discord_user_id
    if victim.rtgg_id:
        user_to_keep.rtgg_id = victim.rtgg_id

    # update everything to the new user
    # we should be figuring this out dynamically by looking at the models
    await models.AsyncTournamentAuditLog.filter(user=victim).update(user=user_to_keep)
    await models.AsyncTournamentPermissions.filter(user=victim).update(user=user_to_keep)
    await models.AsyncTournamentRace.filter(user=victim).update(user=user_to_keep)
    await models.AsyncTournamentRace.filter(reviewed_by=victim).update(reviewed_by=user_to_keep)
    await models.AsyncTournamentReviewNotes.filter(author=victim).update(author=user_to_keep)

    await victim.delete()
    await user_to_keep.save()

    return user_to_keep
