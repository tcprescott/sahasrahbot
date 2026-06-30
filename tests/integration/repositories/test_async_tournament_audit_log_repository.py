"""Repository round-trip tests against an in-memory SQLite database.

See alttprbot/repositories/async_tournament_audit_log_repository.py.
"""

from alttprbot import models
from alttprbot.repositories import AsyncTournamentAuditLogRepository


async def make_tournament(channel_id=1):
    return await models.AsyncTournament.create(
        name="fixture", guild_id=1, channel_id=channel_id, owner_id=1
    )


async def test_record_persists_without_user(tortoise_db):
    tournament = await make_tournament()

    created = await AsyncTournamentAuditLogRepository.record(
        tournament_id=tournament.id,
        action="async.race_finished",
        details="finished in 1:23:45",
    )

    fetched = await models.AsyncTournamentAuditLog.get(id=created.id)
    assert fetched.tournament_id == tournament.id
    assert fetched.action == "async.race_finished"
    assert fetched.details == "finished in 1:23:45"
    assert fetched.user_id is None


async def test_record_links_user_when_provided(tortoise_db):
    tournament = await make_tournament(channel_id=2)
    user = await models.Users.create(discord_user_id=99, display_name="racer")

    created = await AsyncTournamentAuditLogRepository.record(
        tournament_id=tournament.id,
        action="async.race_reviewed",
        user_id=user.id,
        details=None,
    )

    fetched = await models.AsyncTournamentAuditLog.get(id=created.id)
    assert fetched.user_id == user.id
    assert fetched.details is None
