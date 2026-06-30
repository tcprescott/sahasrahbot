"""Characterization tests for the SM Dash provider adapter.

Targets ``SMDashProvider`` from alttprbot/services/seedgen/provider_adapters.py. The
legacy smdash helpers are mocked so no HTTP is made; backoff sleep is patched.
"""

import asyncio
from unittest.mock import AsyncMock

import aiohttp
import pytest

from alttprbot.services.seedgen import provider_adapters
from alttprbot.services.seedgen.provider_adapters import SMDashProvider
from alttprbot.services.seedgen.provider_exceptions import (
    SeedProviderResponseFormatError,
    SeedProviderUnavailableError,
)


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())


@pytest.fixture
def mock_create(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(provider_adapters.smdash_legacy, "create_smdash", mock)
    return mock


async def test_generate_seed_extracts_hash_from_url(mock_create):
    mock_create.return_value = "https://www.dashrando.net/seed/ABC123"
    resp = await SMDashProvider.generate_seed(mode="classic_mm", surface="discord")
    assert resp.url == "https://www.dashrando.net/seed/ABC123"
    assert resp.hash_or_id == "ABC123"
    assert resp.provider_meta.provider == "smdash"
    assert resp.provider_meta.attempt_count == 1
    assert resp.provider_meta.surface == "discord"
    assert resp.code is None


async def test_generate_seed_strips_trailing_slash(mock_create):
    mock_create.return_value = "https://www.dashrando.net/seed/XYZ/"
    resp = await SMDashProvider.generate_seed()
    assert resp.hash_or_id == "XYZ"


async def test_generate_seed_spoiler_sets_spoiler_url(mock_create):
    mock_create.return_value = "https://www.dashrando.net/seed/S1"
    resp = await SMDashProvider.generate_seed(spoiler=True)
    assert resp.spoiler_url == "https://www.dashrando.net/seed/S1"


async def test_generate_seed_passes_mode_and_spoiler_through(mock_create):
    mock_create.return_value = "https://www.dashrando.net/seed/Q"
    await SMDashProvider.generate_seed(mode="mm_eris", spoiler=True)
    mock_create.assert_awaited_once_with(mode="mm_eris", spoiler=True)


@pytest.mark.parametrize("bad", ["", None, 12345])
async def test_generate_seed_invalid_url_raises_format_error(mock_create, bad):
    mock_create.return_value = bad
    with pytest.raises(SeedProviderResponseFormatError):
        await SMDashProvider.generate_seed()


async def test_generate_seed_connection_error_is_retried_and_normalized(mock_create, no_sleep):
    mock_create.side_effect = aiohttp.ClientConnectionError()
    with pytest.raises(SeedProviderUnavailableError) as exc:
        await SMDashProvider.generate_seed()
    assert exc.value.attempts == 3
    assert exc.value.provider == "smdash"


async def test_get_presets_returns_legacy_list(monkeypatch):
    monkeypatch.setattr(
        provider_adapters.smdash_legacy,
        "get_smdash_presets",
        AsyncMock(return_value=["classic_mm", "mm_eris"]),
    )
    assert await SMDashProvider.get_presets() == ["classic_mm", "mm_eris"]
