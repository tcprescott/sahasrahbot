"""Characterization tests for the provider reliability contract.

Targets ``_is_retryable_error`` and ``execute_with_contract`` from
alttprbot/services/seedgen/provider_wrapper.py. External HTTP is never made; the
provider callable is an ``AsyncMock`` and ``asyncio.sleep`` is patched so the
exponential backoff does not actually wait.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from alttprbot.services.seedgen import provider_wrapper
from alttprbot.services.seedgen.provider_wrapper import (
    _is_retryable_error,
    execute_with_contract,
)
from alttprbot.services.seedgen.provider_exceptions import (
    SeedProviderInvalidRequestError,
    SeedProviderRateLimitError,
    SeedProviderResponseFormatError,
    SeedProviderTimeoutError,
    SeedProviderUnavailableError,
)
from alttprbot.services.seedgen.provider_response import ProviderMetadata, ProviderResponse


def http_error(status, message="boom"):
    return aiohttp.ClientResponseError(MagicMock(), (), status=status, message=message)


def make_response(surface=None):
    return ProviderResponse(
        url="https://alttpr.com/h/ABCDE",
        hash_or_id="ABCDE",
        provider_meta=ProviderMetadata(
            provider="p", operation="op", attempt_count=0, latency_ms=0, surface=surface
        ),
    )


@pytest.fixture
def no_sleep(monkeypatch):
    """Make tenacity's backoff instantaneous."""
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())


# ---- _is_retryable_error ------------------------------------------------

@pytest.mark.parametrize(
    "exc",
    [
        asyncio.TimeoutError(),
        aiohttp.ClientConnectionError(),
        SeedProviderTimeoutError("m", provider="p", operation="o"),
        SeedProviderUnavailableError("m", provider="p", operation="o"),
        SeedProviderRateLimitError("m", provider="p", operation="o"),
    ],
)
def test_retryable_true(exc):
    assert _is_retryable_error(exc) is True


@pytest.mark.parametrize(
    "exc",
    [
        SeedProviderInvalidRequestError("m", provider="p", operation="o"),
        SeedProviderResponseFormatError("m", provider="p", operation="o"),
        ValueError("unexpected"),
    ],
)
def test_retryable_false(exc):
    assert _is_retryable_error(exc) is False


@pytest.mark.parametrize(
    "status, expected",
    [(429, True), (500, True), (503, True), (400, False), (404, False), (302, False), (600, False)],
)
def test_retryable_http_status(status, expected):
    # 302/600 pin the default-deny fallthrough for statuses outside 4xx/5xx.
    assert _is_retryable_error(http_error(status)) is expected


# ---- execute_with_contract: success paths -------------------------------

async def test_success_first_attempt_enriches_metadata():
    provider = AsyncMock(return_value=make_response())
    result = await execute_with_contract(provider, "p", "op", surface="discord")
    assert result.provider_meta.attempt_count == 1
    assert result.provider_meta.surface == "discord"
    assert result.provider_meta.latency_ms >= 0
    provider.assert_awaited_once()


async def test_non_provider_response_passes_through_unchanged():
    provider = AsyncMock(return_value=["open", "casualboots"])
    result = await execute_with_contract(provider, "p", "get_presets")
    assert result == ["open", "casualboots"]
    provider.assert_awaited_once()


async def test_existing_surface_is_not_overwritten():
    # The wrapper only sets surface when the response left it unset.
    provider = AsyncMock(return_value=make_response(surface="api"))
    result = await execute_with_contract(provider, "p", "op", surface="discord")
    assert result.provider_meta.surface == "api"


async def test_retries_then_succeeds(no_sleep):
    provider = AsyncMock(side_effect=[aiohttp.ClientConnectionError(), make_response()])
    result = await execute_with_contract(provider, "p", "op")
    assert result.provider_meta.attempt_count == 2
    assert provider.await_count == 2


# ---- execute_with_contract: failure normalization -----------------------

async def test_exhausts_retries_on_connection_error(no_sleep):
    provider = AsyncMock(side_effect=aiohttp.ClientConnectionError())
    with pytest.raises(SeedProviderUnavailableError) as exc:
        await execute_with_contract(provider, "alttpr", "op")
    # The escaping exception is the normalized error, never a tenacity RetryError.
    assert type(exc.value) is SeedProviderUnavailableError
    assert exc.value.attempts == 3
    assert exc.value.provider == "alttpr"
    assert provider.await_count == 3


async def test_timeout_is_normalized_and_retried(no_sleep):
    provider = AsyncMock(side_effect=asyncio.TimeoutError())
    with pytest.raises(SeedProviderTimeoutError) as exc:
        await execute_with_contract(provider, "p", "op")
    assert exc.value.attempts == 3
    assert provider.await_count == 3


async def test_rate_limit_is_retried(no_sleep):
    provider = AsyncMock(side_effect=http_error(429, "slow down"))
    with pytest.raises(SeedProviderRateLimitError) as exc:
        await execute_with_contract(provider, "p", "op")
    assert exc.value.status_code == 429
    assert exc.value.attempts == 3
    # The upstream message is propagated into provider_message.
    assert exc.value.provider_message == "slow down"


async def test_client_4xx_is_not_retried():
    provider = AsyncMock(side_effect=http_error(400, "bad request"))
    with pytest.raises(SeedProviderInvalidRequestError) as exc:
        await execute_with_contract(provider, "p", "op")
    assert exc.value.status_code == 400
    assert exc.value.attempts == 1
    provider.assert_awaited_once()


async def test_unexpected_error_wrapped_as_format_error():
    provider = AsyncMock(side_effect=ValueError("malformed json"))
    with pytest.raises(SeedProviderResponseFormatError) as exc:
        await execute_with_contract(provider, "p", "op")
    # Unknown errors are not retryable, so only one attempt is made.
    assert exc.value.attempts == 1
    provider.assert_awaited_once()
