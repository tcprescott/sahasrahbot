"""Round-trip tests for repositories introduced during the cog burn-down."""

from alttprbot import models
from alttprbot.repositories import (
    InquiryMessageConfigRepository,
    ScheduledEventsRepository,
    TournamentPresetHistoryRepository,
)


async def test_inquiry_message_config_create_get(tortoise_db):
    assert await InquiryMessageConfigRepository.get_by_message_id(123) is None

    created = await InquiryMessageConfigRepository.create(message_id=123, role_id=456)
    assert created.role_id == 456

    fetched = await InquiryMessageConfigRepository.get_by_message_id(123)
    assert fetched is not None and fetched.role_id == 456


async def test_scheduled_events_crud_and_dead_filter(tortoise_db):
    await ScheduledEventsRepository.create(scheduled_event_id=1, episode_id=10, event_slug="ev")
    got = await ScheduledEventsRepository.get_by_episode(10)
    assert got is not None and got.scheduled_event_id == 1

    # episode 10 is "dead" when not in the active list, but not when present
    dead = await ScheduledEventsRepository.list_dead([99], "ev")
    assert [d.episode_id for d in dead] == [10]
    assert await ScheduledEventsRepository.list_dead([10], "ev") == []
    # event_slug scoping
    assert await ScheduledEventsRepository.list_dead([99], "other") == []

    _, created = await ScheduledEventsRepository.upsert_by_episode(
        20, scheduled_event_id=2, event_slug="ev"
    )
    assert created is True

    await ScheduledEventsRepository.delete_instance(got)
    assert await ScheduledEventsRepository.get_by_episode(10) is None


async def test_tournament_preset_history_delete_for_episode(tortoise_db):
    await models.TournamentPresetHistory.create(
        preset="open", discord_user_id=1, episode_id=10, event_slug="cc2023"
    )
    await models.TournamentPresetHistory.create(
        preset="open", discord_user_id=1, episode_id=11, event_slug="other"
    )

    assert await TournamentPresetHistoryRepository.delete_for_episode(10, "cc2023") == 1
    assert await TournamentPresetHistoryRepository.delete_for_episode(10, "cc2023") == 0
    # the unrelated row is untouched
    assert await models.TournamentPresetHistory.get_or_none(episode_id=11) is not None
