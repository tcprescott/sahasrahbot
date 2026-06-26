"""DailyService unit tests: the new-daily decision with a mocked repository.

See alttprbot/services/daily_service.py. The service owns the "is this hash new?"
rule; the repository (mocked here) owns the actual ORM access.
"""

import pytest
from unittest.mock import AsyncMock

from alttprbot.services import DailyService


async def test_record_if_new_records_and_returns_true_when_unseen():
    service = DailyService()
    service.daily_repository = AsyncMock()
    service.daily_repository.exists_by_hash.return_value = False

    result = await service.record_if_new("ABCDE")

    assert result is True
    service.daily_repository.exists_by_hash.assert_awaited_once_with("ABCDE")
    service.daily_repository.create.assert_awaited_once_with("ABCDE")


async def test_record_if_new_skips_and_returns_false_when_known():
    service = DailyService()
    service.daily_repository = AsyncMock()
    service.daily_repository.exists_by_hash.return_value = True

    result = await service.record_if_new("ABCDE")

    assert result is False
    service.daily_repository.exists_by_hash.assert_awaited_once_with("ABCDE")
    service.daily_repository.create.assert_not_awaited()


async def test_record_if_new_rejects_empty_hash():
    service = DailyService()
    service.daily_repository = AsyncMock()

    with pytest.raises(ValueError):
        await service.record_if_new("")

    service.daily_repository.exists_by_hash.assert_not_awaited()
    service.daily_repository.create.assert_not_awaited()
