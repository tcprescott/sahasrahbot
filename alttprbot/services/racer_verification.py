"""Racer verification: whether a member has raced enough to earn a guild's
verified-racer role, counted from racetime.gg and the ALTTPR Ladder.

The Discord side (the button, the role, the replies) is in
``alttprbot_discord/cogs/racer_verification.py``.
"""
from datetime import datetime, timedelta, timezone

import isodate

from alttprbot import models
from alttprbot.integrations import alttprladder, racetime
from alttprbot.services import audit


async def get_for_message(message_id: int, guild_id: int):
    """The verification set up on this message, or None."""
    return await models.RacerVerification.get_or_none(message_id=message_id, guild_id=guild_id)


async def get_linked_user(discord_user_id: int):
    """The SahasrahBot user with a linked racetime.gg account, or None if either is missing."""
    user = await models.Users.get_or_none(discord_user_id=discord_user_id)
    if user is None or user.rtgg_id is None:
        return None
    return user


async def create_or_update(guild_id: int, role_id: int, **settings) -> models.RacerVerification:
    racer_verification, created = await models.RacerVerification.update_or_create(
        role_id=role_id,
        guild_id=guild_id,
        defaults=settings,
    )
    await audit.record(audit.RACER_VERIFICATION_CONFIGURED, target=f'Role {role_id}', guild_id=guild_id,
                       details={'racer_verification_id': racer_verification.id, 'role_id': role_id,
                                'created': created, 'settings': settings})
    return racer_verification


async def attach_message(racer_verification: models.RacerVerification, message_id: int, channel_id: int) -> None:
    racer_verification.message_id = message_id
    racer_verification.channel_id = channel_id
    await racer_verification.save()


async def record_verified(user: models.Users, racer_verification: models.RacerVerification, count: int,
                          now: datetime = None) -> models.VerifiedRacer:
    """Create or refresh the user's VerifiedRacer row."""
    now = now or datetime.now(timezone.utc)
    racer = await models.VerifiedRacer.get_or_none(user=user, racer_verification=racer_verification)
    if racer is None:
        racer = await models.VerifiedRacer.create(
            user=user,
            racer_verification=racer_verification,
            last_verified=now,
            estimated_count=count
        )
        await audit.record(audit.RACER_VERIFICATION_VERIFIED, target=f'Role {racer_verification.role_id}',
                           guild_id=racer_verification.guild_id, actor_discord_id=user.discord_user_id,
                           details={'racer_verification_id': racer_verification.id, 'race_count': count})
        return racer
    racer.last_verified = now
    racer.estimated_count = count
    await racer.save()
    return racer


async def get_racetime_count(racetime_id, category_slugs=None, days=365, max_count=1):
    """Finished races in these categories opened in the last ``days`` days.

    Stops paging once ``max_count`` is reached, so the result is "at least".
    """
    page = 1
    count = 0
    if category_slugs is None:
        return 0

    while count < max_count:
        data = await racetime.get_user_races_page(racetime_id, page)
        if data is None:
            break

        if len(data['races']) == 0:
            break

        filtered_data = [x for x in data['races']
                         if x['category']['slug'] in category_slugs
                         and x['status']['value'] == 'finished'
                         and tz_aware_greater_than(isodate.parse_datetime(x['opened_at']),
                                                   datetime.now(timezone.utc) - timedelta(days=days))
                         ]

        count += len(filtered_data)

        if page > data['num_pages']:
            break

        page += 1

    return count


def tz_aware_greater_than(dt1, dt2):
    if dt1.tzinfo is None:
        dt1 = dt1.replace(tzinfo=timezone.utc)
    if dt2.tzinfo is None:
        dt2 = dt2.replace(tzinfo=timezone.utc)
    return dt1 > dt2


async def get_ladder_count(discord_username, days=365):
    racer_guid = await alttprladder.get_racer_guid(discord_username)
    data = await alttprladder.get_racer_history(racer_guid)

    cutoff = datetime.now() - timedelta(days=days)
    return sum(
        len([race for race in flag['Results']
             if datetime.fromisoformat(race['StartDateTime']) > cutoff])
        for flag in data
    )


# This will be deprecated in the future once we've had ladder 2.0 for a year.
async def get_ladder_archive_count(discord_id, days=365):
    now = datetime.now()
    return await alttprladder.get_archive_race_count(discord_id, start=now - timedelta(days=days), end=now)


async def determine_eligibility(username: str, user: models.Users, racer_verification: models.RacerVerification):
    """``(eligible, race_count)``: ladder races first (when enabled), then racetime.gg
    races if the ladder alone doesn't reach ``minimum_races``."""
    try:
        rtgg_categories = racer_verification.racetime_categories.split(',')
    except AttributeError:
        rtgg_categories = []

    race_count = 0

    if racer_verification.use_alttpr_ladder:
        race_count += await get_ladder_count(username, days=racer_verification.time_period_days)
        race_count += await get_ladder_archive_count(user.discord_user_id, days=racer_verification.time_period_days)

    if race_count < racer_verification.minimum_races:
        race_count += await get_racetime_count(user.rtgg_id, rtgg_categories,
                                               days=racer_verification.time_period_days,
                                               max_count=racer_verification.minimum_races)

    return race_count >= racer_verification.minimum_races, race_count
