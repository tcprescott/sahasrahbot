"""Racer verification: whether a member has raced enough to earn a guild's
verified-racer role, counted from racetime.gg and the ALTTPR Ladder.

A server's Administrators set it up on the website (the Verification section of a
server) or with ``/racerverification``. Members press the button on the posted
message; the Discord side (the button, the role, the replies) is in
``alttprbot_discord/racer_verification.py`` and ``alttprbot_discord/cogs/racer_verification.py``.

When ``reverify_period_days`` is set, :func:`recheck_due` (a scheduled job) counts
each verified racer's races again once that many days have passed since their last
check. With ``revoke_ineligible`` it takes the role from anyone who no longer
qualifies or has left the server; either way it publishes
``RacerVerificationRechecked`` so the audit channel hears who changed. Only people who
verified with the button have a ``VerifiedRacer`` row, so only they are rechecked:
listing a role's members would need the privileged members intent.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol

import isodate

from alttprbot import events, models
from alttprbot.exceptions import InvalidInputError, NotFoundError, PermissionDeniedError
from alttprbot.integrations import alttprladder, racetime
from alttprbot.services import audit, discord_directory

logger = logging.getLogger(__name__)

# The racetime.gg categories the settings form offers. Others saved before stay valid.
RACETIME_CATEGORIES = ('alttpr', 'smz3', 'smr', 'z1r', 'z2r', 'twwr', 'ff1r', 'ct-jets')
MAX_MINIMUM_RACES = 1000
MAX_DAYS = 3650


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


# --- Discord, as the service needs it ---------------------------------------------

class Gateway(Protocol):
    """What the service needs from Discord. ``alttprbot_discord.gateways.register()``
    registers the bot's implementation; tests and the dev server register fakes."""

    async def post_message(self, channel_id: int, content: str) -> int:
        """Post ``content`` with the "Verify your status" button; return the message id.
        Raises ``InvalidInputError`` with a readable reason when it can't."""

    async def edit_message(self, channel_id: int, message_id: int, content: str) -> bool:
        """Replace the message's text. False when the message is gone."""

    async def delete_message(self, channel_id: int, message_id: int) -> None:
        """Delete the message, if it's still there."""

    async def member_name(self, guild_id: int, user_id: int) -> Optional[str]:
        """The member's Discord username, or None when they aren't in the server."""

    async def remove_role(self, guild_id: int, user_id: int, role_id: int, reason: str) -> None:
        """Take the role from the member. Does nothing if they've left."""


_gateway: Optional[Gateway] = None


def register(gateway: Gateway) -> None:
    global _gateway
    _gateway = gateway


def gateway() -> Gateway:
    if _gateway is None:
        raise RuntimeError("No racer verification gateway registered; call alttprbot_discord.gateways.register().")
    return _gateway


# --- Managing a server's verifications (the website and API) ----------------------

@dataclass
class VerificationInput:
    role_id: int
    channel_id: int
    racetime_categories: list[str] = field(default_factory=list)
    use_alttpr_ladder: bool = False
    minimum_races: int = 1
    time_period_days: int = 365
    reverify_period_days: Optional[int] = None
    revoke_ineligible: bool = False
    audit_channel_id: Optional[int] = None


async def _require_admin(guild_id: int, user_id: int) -> None:
    directory = discord_directory.get()
    if await directory.is_owner(user_id) or await directory.is_admin(guild_id, user_id):
        return
    raise PermissionDeniedError("Only administrators of that server can manage its racer verification.")


async def _admin_verification(verification_id: int, user_id: int) -> models.RacerVerification:
    rv = await models.RacerVerification.get_or_none(id=verification_id)
    if rv is None:
        raise NotFoundError("That racer verification doesn't exist.")
    await _require_admin(rv.guild_id, user_id)
    return rv


def categories_of(rv: models.RacerVerification) -> list[str]:
    return [c.strip() for c in (rv.racetime_categories or '').split(',') if c.strip()]


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def requirement(rv) -> str:
    """"5 races in 365 days"."""
    return f"{_plural(rv.minimum_races, 'race')} in {_plural(rv.time_period_days, 'day')}"


def message_content(rv) -> str:
    """The text of the message with the "Verify your status" button."""
    sources = categories_of(rv)
    counted = ', '.join(sources) if sources else 'no categories'
    content = f"""
This message will be used to verify your status as a racer. You can click the button below to verify your status.
You must have a RaceTime.gg account linked to your Discord account to use this feature.
If you do not have a RaceTime.gg account, please visit <https://racetime.gg> to create one.

If you have any questions, please contact a server administrator.

**Requirements:**
- Must have a RaceTime.gg account linked to your Discord account via SahasrahBot.  You will be supplied a link to do so if this is not already done.
- Have at least {_plural(rv.minimum_races, 'race')} played in the last {_plural(rv.time_period_days, 'day')} on RaceTime.gg in the following categories: {counted}{' or ALTTPR Ladder races' if rv.use_alttpr_ladder else ''}
- Must be a member of this Discord server
"""
    if rv.reverify_period_days:
        content += (f"- Your races are counted again every {_plural(rv.reverify_period_days, 'day')}. "
                    "This is automatic and needs nothing from you.\n")
    return content


def _validate(data: VerificationInput) -> None:
    if not 1 <= data.minimum_races <= MAX_MINIMUM_RACES:
        raise InvalidInputError(f"Races needed must be between 1 and {MAX_MINIMUM_RACES}.")
    if not 1 <= data.time_period_days <= MAX_DAYS:
        raise InvalidInputError(f"The counting period must be between 1 and {MAX_DAYS} days.")
    if data.reverify_period_days is not None and not 1 <= data.reverify_period_days <= MAX_DAYS:
        raise InvalidInputError(f"Recheck every must be between 1 and {MAX_DAYS} days, or empty.")
    if not data.racetime_categories and not data.use_alttpr_ladder:
        raise InvalidInputError("Pick at least one racetime.gg category, or count ALTTPR Ladder races.")
    for slug in data.racetime_categories:
        if not slug or len(slug) > 50 or not all(c.isalnum() or c == '-' for c in slug):
            raise InvalidInputError(f"{slug!r} isn't a racetime.gg category.")


async def _check_ids(guild_id: int, data: VerificationInput) -> None:
    directory = discord_directory.get()
    if data.role_id not in {r.id for r in await directory.roles(guild_id)}:
        raise InvalidInputError("That role isn't in this server, or SahasrahBot can't give it.")
    channels = {c.id for c in await directory.text_channels(guild_id)}
    if data.channel_id not in channels:
        raise InvalidInputError("SahasrahBot can't post in that channel.")
    if data.audit_channel_id is not None and data.audit_channel_id not in channels:
        raise InvalidInputError("SahasrahBot can't post in the channel for reports.")


def _settings(data: VerificationInput) -> dict:
    return {
        'role_id': data.role_id,
        'racetime_categories': ','.join(dict.fromkeys(data.racetime_categories)) or None,
        'use_alttpr_ladder': data.use_alttpr_ladder,
        'minimum_races': data.minimum_races,
        'time_period_days': data.time_period_days,
        'reverify_period_days': data.reverify_period_days,
        'revoke_ineligible': data.revoke_ineligible and data.reverify_period_days is not None,
        'audit_channel_id': data.audit_channel_id,
    }


def _plain_settings(rv) -> dict:
    return {
        'role_id': rv.role_id, 'channel_id': rv.channel_id, 'racetime_categories': rv.racetime_categories,
        'use_alttpr_ladder': rv.use_alttpr_ladder, 'minimum_races': rv.minimum_races,
        'time_period_days': rv.time_period_days, 'reverify_period_days': rv.reverify_period_days,
        'revoke_ineligible': rv.revoke_ineligible, 'audit_channel_id': rv.audit_channel_id,
    }


async def _summary(rv: models.RacerVerification, names: Optional[dict] = None) -> dict:
    if names is None:
        names = await _names(rv.guild_id)
    return {
        'id': rv.id,
        'guild_id': rv.guild_id,
        'role_id': rv.role_id,
        'role_name': names['roles'].get(rv.role_id),
        'channel_id': rv.channel_id,
        'channel_name': names['channels'].get(rv.channel_id),
        'message_id': rv.message_id,
        'racetime_categories': categories_of(rv),
        'use_alttpr_ladder': rv.use_alttpr_ladder,
        'minimum_races': rv.minimum_races,
        'time_period_days': rv.time_period_days,
        'reverify_period_days': rv.reverify_period_days,
        'revoke_ineligible': rv.revoke_ineligible,
        'audit_channel_id': rv.audit_channel_id,
        'audit_channel_name': names['channels'].get(rv.audit_channel_id),
        'requirement': requirement(rv),
        'verified_count': await models.VerifiedRacer.filter(racer_verification_id=rv.id).count(),
    }


async def _names(guild_id: int) -> dict:
    directory = discord_directory.get()
    return {
        'roles': {r.id: r.name for r in await directory.roles(guild_id)},
        'channels': {c.id: c.name for c in await directory.text_channels(guild_id)},
    }


async def list_for_guild(guild_id: int, user_id: int) -> list[dict]:
    """The server's verifications, for its Verification section."""
    await _require_admin(guild_id, user_id)
    names = await _names(guild_id)
    return [await _summary(rv, names)
            for rv in await models.RacerVerification.filter(guild_id=guild_id).order_by('id')]


async def get_for_admin(verification_id: int, user_id: int) -> dict:
    return await _summary(await _admin_verification(verification_id, user_id))


async def _post(rv: models.RacerVerification) -> None:
    rv.message_id = await gateway().post_message(rv.channel_id, message_content(rv))
    await rv.save()


async def create(guild_id: int, user_id: int, data: VerificationInput) -> dict:
    """Save a new verification and post its button message."""
    await _require_admin(guild_id, user_id)
    _validate(data)
    await _check_ids(guild_id, data)
    if await models.RacerVerification.exists(guild_id=guild_id, role_id=data.role_id):
        raise InvalidInputError("That role already has racer verification. Edit it instead.")
    rv = await models.RacerVerification.create(guild_id=guild_id, channel_id=data.channel_id, **_settings(data))
    try:
        await _post(rv)
    except Exception:
        await rv.delete()
        raise
    await audit.record(audit.RACER_VERIFICATION_CONFIGURED, target=f'Role {rv.role_id}', guild_id=guild_id,
                       details={'racer_verification_id': rv.id, 'role_id': rv.role_id, 'created': True,
                                'settings': _plain_settings(rv)})
    return await _summary(rv)


async def update(verification_id: int, user_id: int, data: VerificationInput) -> dict:
    """Change the settings and update the Discord message (posting it anew in a new channel)."""
    rv = await _admin_verification(verification_id, user_id)
    _validate(data)
    await _check_ids(rv.guild_id, data)
    if data.role_id != rv.role_id and await models.RacerVerification.exists(guild_id=rv.guild_id,
                                                                             role_id=data.role_id):
        raise InvalidInputError("That role already has racer verification.")
    before = _plain_settings(rv)
    old_channel, old_message = rv.channel_id, rv.message_id
    for key, value in _settings(data).items():
        setattr(rv, key, value)
    rv.channel_id = data.channel_id
    await rv.save()
    if old_channel != rv.channel_id or not old_message:
        await _post(rv)
        if old_channel and old_message:
            await gateway().delete_message(old_channel, old_message)
    elif not await gateway().edit_message(rv.channel_id, rv.message_id, message_content(rv)):
        await _post(rv)
    changes = audit.changes(before, _plain_settings(rv))
    if changes:
        await audit.record(audit.RACER_VERIFICATION_UPDATED, target=f'Role {rv.role_id}', guild_id=rv.guild_id,
                           details={'racer_verification_id': rv.id, 'changes': changes})
    return await _summary(rv)


async def repost(verification_id: int, user_id: int) -> dict:
    """Post the button message again (say, after someone deleted it) and delete the old one."""
    rv = await _admin_verification(verification_id, user_id)
    old_message = rv.message_id
    await _post(rv)
    if old_message:
        await gateway().delete_message(rv.channel_id, old_message)
    await audit.record(audit.RACER_VERIFICATION_REPOSTED, target=f'Role {rv.role_id}', guild_id=rv.guild_id,
                       details={'racer_verification_id': rv.id})
    return await _summary(rv)


async def delete(verification_id: int, user_id: int) -> None:
    """Delete the verification, its button message and its list of verified racers.
    Nobody loses the role."""
    rv = await _admin_verification(verification_id, user_id)
    if rv.channel_id and rv.message_id:
        await gateway().delete_message(rv.channel_id, rv.message_id)
    count = await models.VerifiedRacer.filter(racer_verification_id=rv.id).count()
    await rv.delete()
    await audit.record(audit.RACER_VERIFICATION_DELETED, target=f'Role {rv.role_id}', guild_id=rv.guild_id,
                       details={'racer_verification_id': rv.id, 'verified_racers': count})


# --- Verified racers ----------------------------------------------------------------

OK = 'verified'
DUE = 'due'
FAILING = 'not_qualified'


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def next_check(rv, racer) -> Optional[datetime]:
    last = _aware(racer.last_verified or racer.created)
    if not rv.reverify_period_days or last is None:
        return None
    return last + timedelta(days=rv.reverify_period_days)


def racer_status(rv, racer, now: datetime) -> str:
    if racer.estimated_count is not None and racer.estimated_count < rv.minimum_races:
        return FAILING
    due = next_check(rv, racer)
    if due is not None and due <= now:
        return DUE
    return OK


def _racer_view(rv, racer, now: datetime) -> dict:
    user = racer.user
    return {
        'id': racer.id,
        'discord_user_id': user.discord_user_id,
        'name': user.display_name,
        'racetime_id': user.rtgg_id,
        'racetime_url': user.racetime_profile,
        'race_count': racer.estimated_count,
        'verified_at': racer.created,
        'last_checked': racer.last_verified,
        'next_check': next_check(rv, racer),
        'status': racer_status(rv, racer, now),
    }


async def list_racers(verification_id: int, user_id: int, now: Optional[datetime] = None) -> list[dict]:
    """Everyone verified through this verification's button, most recently checked first."""
    rv = await _admin_verification(verification_id, user_id)
    now = now or datetime.now(timezone.utc)
    racers = await models.VerifiedRacer.filter(racer_verification_id=rv.id).prefetch_related('user') \
        .order_by('-last_verified', '-id')
    return [_racer_view(rv, r, now) for r in racers]


async def _admin_racer(verification_id: int, racer_id: int, user_id: int):
    rv = await _admin_verification(verification_id, user_id)
    racer = await models.VerifiedRacer.get_or_none(id=racer_id, racer_verification_id=rv.id).prefetch_related('user')
    if racer is None:
        raise NotFoundError("That racer isn't verified here.")
    return rv, racer


async def remove_racer(verification_id: int, racer_id: int, user_id: int) -> None:
    """Take the role from a verified racer and forget their verification."""
    rv, racer = await _admin_racer(verification_id, racer_id, user_id)
    await gateway().remove_role(rv.guild_id, racer.user.discord_user_id, rv.role_id,
                                reason="Racer verification removed by an administrator")
    await racer.delete()
    await audit.record(audit.RACER_VERIFICATION_REVOKED, target=f'Role {rv.role_id}', guild_id=rv.guild_id,
                       details={'racer_verification_id': rv.id, 'racer_discord_id': racer.user.discord_user_id,
                                'reason': 'removed'})


@dataclass
class RecheckOutcome:
    """What a recheck found: ``kept`` still qualifies; ``revoked`` lost the role;
    ``failing`` no longer qualifies but kept it (revoke is off); ``left`` left the server."""
    kept: list[str] = field(default_factory=list)
    revoked: list[str] = field(default_factory=list)
    failing: list[str] = field(default_factory=list)
    left: list[str] = field(default_factory=list)


async def _recheck(rv: models.RacerVerification, racer: models.VerifiedRacer, outcome: RecheckOutcome,
                   now: datetime) -> str:
    """Count one racer's races again. Returns ``kept``, ``revoked``, ``failing`` or ``left``."""
    user = racer.user
    label = user.display_name or str(user.discord_user_id)
    username = await gateway().member_name(rv.guild_id, user.discord_user_id)
    if username is None:
        await racer.delete()
        outcome.left.append(label)
        await audit.record(audit.RACER_VERIFICATION_REVOKED, target=f'Role {rv.role_id}', guild_id=rv.guild_id,
                           details={'racer_verification_id': rv.id, 'racer_discord_id': user.discord_user_id,
                                    'reason': 'left_server'})
        return 'left'
    eligible, count = await determine_eligibility(username, user, rv)
    if eligible:
        racer.last_verified = now
        racer.estimated_count = count
        await racer.save()
        outcome.kept.append(label)
        return 'kept'
    if rv.revoke_ineligible:
        await gateway().remove_role(rv.guild_id, user.discord_user_id, rv.role_id,
                                    reason="No longer meets the racer verification requirements")
        await racer.delete()
        outcome.revoked.append(label)
        await audit.record(audit.RACER_VERIFICATION_REVOKED, target=f'Role {rv.role_id}', guild_id=rv.guild_id,
                           details={'racer_verification_id': rv.id, 'racer_discord_id': user.discord_user_id,
                                    'reason': 'not_qualified', 'race_count': count})
        return 'revoked'
    racer.last_verified = now
    racer.estimated_count = count
    await racer.save()
    outcome.failing.append(label)
    return 'failing'


def _publish(rv: models.RacerVerification, outcome: RecheckOutcome) -> None:
    if not (outcome.revoked or outcome.failing or outcome.left):
        return
    events.publish(events.RacerVerificationRechecked(
        racer_verification_id=rv.id,
        guild_id=rv.guild_id,
        role_id=rv.role_id,
        audit_channel_id=rv.audit_channel_id,
        revoked=tuple(outcome.revoked),
        not_qualified=tuple(outcome.failing),
        left=tuple(outcome.left),
    ))


async def recheck_racer(verification_id: int, racer_id: int, user_id: int,
                        now: Optional[datetime] = None) -> Optional[dict]:
    """Count one racer's races now, as the scheduled recheck would. Returns the racer's
    row, or None when the recheck removed it."""
    rv, racer = await _admin_racer(verification_id, racer_id, user_id)
    now = now or datetime.now(timezone.utc)
    outcome = RecheckOutcome()
    result = await _recheck(rv, racer, outcome, now)
    _publish(rv, outcome)
    return _racer_view(rv, racer, now) if result in ('kept', 'failing') else None


# Racers rechecked per verification per run, so one big server can't hold the job
# (or racetime.gg) for long; the rest are picked up on the next run.
RECHECK_BATCH = 50


async def recheck_due(now: Optional[datetime] = None) -> None:
    """The scheduled job: recheck the racers whose recheck is due, in every server."""
    now = now or datetime.now(timezone.utc)
    for rv in await models.RacerVerification.filter(reverify_period_days__isnull=False):
        cutoff = now - timedelta(days=rv.reverify_period_days)
        due = await models.VerifiedRacer.filter(racer_verification_id=rv.id, last_verified__lte=cutoff) \
            .prefetch_related('user').order_by('last_verified').limit(RECHECK_BATCH)
        if not due:
            continue
        outcome = RecheckOutcome()
        for racer in due:
            try:
                await _recheck(rv, racer, outcome, now)
            except Exception:
                # One racer's lookup failing (racetime.gg down, say) mustn't stop the rest.
                logger.warning("Couldn't recheck verified racer %s for verification %s", racer.id, rv.id,
                               exc_info=True)
        _publish(rv, outcome)
