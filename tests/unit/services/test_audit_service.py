"""Reference service test: AuditService delegates to its repositories.

Establishes the Phase 0 pattern — exercise a service with its repository mocked,
asserting the service translates a call into the right repository operation
without touching the database.
"""

from unittest.mock import AsyncMock

from alttprbot.services import AuditActions, AuditService


async def test_record_generated_game_delegates_to_repository():
    service = AuditService()
    service.generated_games_repository = AsyncMock()

    await service.record_generated_game(
        randomizer="alttpr",
        hash_id="ABCDE",
        permalink="https://alttpr.com/h/ABCDE",
        settings={"glitches": "none"},
        gentype="preset",
        genoption="open",
    )

    service.generated_games_repository.record.assert_awaited_once_with(
        randomizer="alttpr",
        hash_id="ABCDE",
        permalink="https://alttpr.com/h/ABCDE",
        settings={"glitches": "none"},
        gentype="preset",
        genoption="open",
        customizer=0,
        doors=False,
        avianart=False,
    )


async def test_record_async_event_maps_actor_to_user_id():
    service = AuditService()
    service.async_log_repository = AsyncMock()

    await service.record_async_event(
        tournament_id=7,
        action=AuditActions.ASYNC_RACE_FINISHED,
        actor_id=42,
        details="finished in 1:23:45",
    )

    service.async_log_repository.record.assert_awaited_once_with(
        tournament_id=7,
        action="async.race_finished",
        user_id=42,
        details="finished in 1:23:45",
    )


def test_audit_action_constants_are_stable():
    # Pin the verb.object action strings; a typo/swap here would silently
    # mislabel audit-log rows.
    assert AuditActions.GAME_GENERATED == "game.generated"
    assert AuditActions.ASYNC_RACE_STARTED == "async.race_started"
    assert AuditActions.ASYNC_RACE_FINISHED == "async.race_finished"
    assert AuditActions.ASYNC_RACE_FORFEITED == "async.race_forfeited"
    assert AuditActions.ASYNC_RACE_REVIEWED == "async.race_reviewed"
