"""Unit tests for services added migrating the audit / rankedchoice / racer cogs."""

import datetime
from unittest.mock import AsyncMock, sentinel

from alttprbot.services import (
    AuditMessagesService,
    RacerVerificationService,
    RankedChoiceService,
    VerifiedRacerService,
)


# --- AuditMessagesService ---

async def test_clean_old_messages_passes_cutoff():
    service = AuditMessagesService()
    service.repository = AsyncMock()

    await service.clean_old_messages(days=30)

    (cutoff,), _ = service.repository.delete_older_than.await_args
    assert isinstance(cutoff, datetime.datetime)


async def test_mark_deleted_delegates():
    service = AuditMessagesService()
    service.repository = AsyncMock()
    await service.mark_deleted(99)
    service.repository.mark_deleted_by_message_id.assert_awaited_once_with(99)


# --- RankedChoiceService (new cog methods) ---

async def test_add_candidates_delegates():
    service = RankedChoiceService()
    service.repository = AsyncMock()
    await service.add_candidates(sentinel.election, ["a", "b"])
    service.repository.bulk_create_candidates.assert_awaited_once_with(sentinel.election, ["a", "b"])


async def test_close_election_delegates():
    service = RankedChoiceService()
    service.repository = AsyncMock()
    await service.close_election(sentinel.election)
    service.repository.close.assert_awaited_once_with(sentinel.election)


# --- RacerVerificationService ---

async def test_configure_returns_model():
    service = RacerVerificationService()
    service.repository = AsyncMock()
    service.repository.upsert_by_role_and_guild.return_value = (sentinel.rv, True)

    result = await service.configure(role_id=1, guild_id=2, defaults={"minimum_races": 5})
    assert result is sentinel.rv


# --- VerifiedRacerService.record_verification (both branches) ---

async def test_record_verification_creates_when_absent():
    service = VerifiedRacerService()
    service.repository = AsyncMock()
    service.repository.get_for_user_and_verification.return_value = None
    service.repository.create.return_value = sentinel.created

    result = await service.record_verification(sentinel.user, sentinel.rv, 12)

    assert result is sentinel.created
    service.repository.create.assert_awaited_once()
    service.repository.update_verification.assert_not_awaited()


async def test_record_verification_updates_when_present():
    service = VerifiedRacerService()
    service.repository = AsyncMock()
    service.repository.get_for_user_and_verification.return_value = sentinel.existing

    result = await service.record_verification(sentinel.user, sentinel.rv, 12)

    assert result is sentinel.existing
    service.repository.create.assert_not_awaited()
    service.repository.update_verification.assert_awaited_once()
    _, kwargs = service.repository.update_verification.await_args
    assert kwargs["estimated_count"] == 12
    assert isinstance(kwargs["last_verified"], datetime.datetime)
