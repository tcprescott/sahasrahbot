"""Characterization tests for the seed-provider exception taxonomy.

See alttprbot/services/seedgen/provider_exceptions.py.
"""

import pytest

from alttprbot.exceptions import SahasrahBotException
from alttprbot.services.seedgen.provider_exceptions import (
    SeedProviderError,
    SeedProviderInvalidRequestError,
    SeedProviderRateLimitError,
    SeedProviderResponseFormatError,
    SeedProviderTimeoutError,
    SeedProviderUnavailableError,
)


def test_captures_all_attributes():
    err = SeedProviderError(
        "internal message",
        provider="alttpr",
        operation="generate",
        attempts=3,
        status_code=500,
        provider_message="upstream boom",
    )
    assert err.provider == "alttpr"
    assert err.operation == "generate"
    assert err.attempts == 3
    assert err.status_code == 500
    assert err.provider_message == "upstream boom"


def test_str_uses_provider_and_provider_message():
    err = SeedProviderError(
        "internal", provider="smdash", operation="create", provider_message="nope"
    )
    assert str(err) == "smdash: nope"


def test_defaults_when_optionals_omitted():
    err = SeedProviderError("boom", provider="alttpr", operation="generate")
    assert err.attempts == 1
    assert err.status_code is None
    # provider_message falls back to the primary message
    assert err.provider_message == "boom"
    assert str(err) == "alttpr: boom"


def test_is_sahasrahbot_exception():
    # SahasrahBotException subclasses are filtered from Sentry, so the taxonomy
    # must inherit from it.
    err = SeedProviderError("x", provider="p", operation="o")
    assert isinstance(err, SahasrahBotException)


@pytest.mark.parametrize(
    "cls",
    [
        SeedProviderTimeoutError,
        SeedProviderUnavailableError,
        SeedProviderRateLimitError,
        SeedProviderInvalidRequestError,
        SeedProviderResponseFormatError,
    ],
)
def test_subclasses_inherit_base_behavior(cls):
    err = cls("msg", provider="p", operation="op", provider_message="pm")
    assert isinstance(err, SeedProviderError)
    assert isinstance(err, SahasrahBotException)
    assert str(err) == "p: pm"
