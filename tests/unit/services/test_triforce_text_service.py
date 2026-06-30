"""TriforceTextService unit tests: validation, moderator authz, approval mapping."""

from unittest.mock import AsyncMock

from alttprbot.services import TriforceTextService


def test_is_valid_line_accepts_allowed_and_rejects_long_or_bad():
    assert TriforceTextService.is_valid_line("Hello world!") is True
    assert TriforceTextService.is_valid_line("") is True
    assert TriforceTextService.is_valid_line("x" * 20) is False  # max 19
    assert TriforceTextService.is_valid_line("nope#%@") is False


async def test_get_moderator_ids_casts_to_int():
    service = TriforceTextService()
    service.repository = AsyncMock()
    service.repository.list_config_values.return_value = ["111", "222"]

    assert await service.get_moderator_ids("pool") == [111, 222]
    service.repository.list_config_values.assert_awaited_once_with("pool", "moderator")


async def test_is_moderator():
    service = TriforceTextService()
    service.repository = AsyncMock()
    service.repository.list_config_values.return_value = ["111"]

    assert await service.is_moderator(111, "pool") is True
    assert await service.is_moderator(999, "pool") is False


async def test_list_texts_maps_approval_filter():
    service = TriforceTextService()
    service.repository = AsyncMock()
    service.repository.list_for_pool.return_value = []

    await service.list_texts("pool", "pending")
    service.repository.list_for_pool.assert_awaited_with("pool", {"approved__isnull": True})

    await service.list_texts("pool", "true")
    service.repository.list_for_pool.assert_awaited_with("pool", {"approved": True})

    await service.list_texts("pool", "anything-else")
    service.repository.list_for_pool.assert_awaited_with("pool", {})
