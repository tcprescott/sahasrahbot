"""Characterization tests for alttprbot/util/telemetry.py.

Only the pure pieces are covered: ``hash_guild_id`` and ``TelemetryEvent``
validation. The salt is read from the module-level ``TELEMETRY_HASH_SALT``
constant (captured at import time), so the salt branch is exercised by patching
that module attribute, not ``config``.
"""

import hashlib

import pytest

from alttprbot.util import telemetry
from alttprbot.util.telemetry import TelemetryEvent, hash_guild_id


def test_hash_with_salt_matches_sha256(monkeypatch):
    monkeypatch.setattr(telemetry, "TELEMETRY_HASH_SALT", "pepper")
    expected = hashlib.sha256(b"123:pepper").hexdigest()
    assert hash_guild_id(123) == expected


def test_hash_with_salt_is_deterministic(monkeypatch):
    monkeypatch.setattr(telemetry, "TELEMETRY_HASH_SALT", "pepper")
    assert hash_guild_id(999) == hash_guild_id(999)


def test_hash_with_salt_distinguishes_ids(monkeypatch):
    monkeypatch.setattr(telemetry, "TELEMETRY_HASH_SALT", "pepper")
    assert hash_guild_id(1) != hash_guild_id(2)


def test_hash_changes_with_salt(monkeypatch):
    # Same guild id, different salts -> different digest. Pins that the salt
    # actually participates in the hash (not just concatenated-and-ignored).
    monkeypatch.setattr(telemetry, "TELEMETRY_HASH_SALT", "pepper")
    with_pepper = hash_guild_id(777)
    monkeypatch.setattr(telemetry, "TELEMETRY_HASH_SALT", "salt2")
    assert hash_guild_id(777) != with_pepper


def test_hash_without_salt_returns_fixed_value(monkeypatch):
    """Without a salt every guild collapses to one fixed hash (privacy fallback)."""
    monkeypatch.setattr(telemetry, "TELEMETRY_HASH_SALT", "")
    fixed = hashlib.sha256(b"no_salt_configured").hexdigest()
    assert hash_guild_id(1) == fixed
    assert hash_guild_id(2) == fixed


def test_event_hashes_guild_id_when_present(monkeypatch):
    monkeypatch.setattr(telemetry, "TELEMETRY_HASH_SALT", "pepper")
    event = TelemetryEvent(
        event_name="discord.generator.invoke",
        surface="discord",
        feature="generator",
        action="invoke",
        status="ok",
        guild_id=4242,
    )
    assert event.guild_hash == hash_guild_id(4242)


def test_event_guild_hash_none_when_no_guild():
    event = TelemetryEvent(
        event_name="api.preset.create",
        surface="api",
        feature="preset",
        action="invoke",
        status="ok",
    )
    assert event.guild_hash is None


@pytest.mark.parametrize("missing_field", ["event_name", "surface", "feature", "action", "status"])
def test_event_requires_core_fields(missing_field):
    kwargs = dict(
        event_name="x",
        surface="discord",
        feature="generator",
        action="invoke",
        status="ok",
    )
    kwargs[missing_field] = ""
    with pytest.raises(ValueError):
        TelemetryEvent(**kwargs)


def test_event_rejects_overlong_event_name():
    with pytest.raises(ValueError):
        TelemetryEvent(
            event_name="x" * 101,
            surface="discord",
            feature="generator",
            action="invoke",
            status="ok",
        )


def test_event_rejects_overlong_surface():
    with pytest.raises(ValueError):
        TelemetryEvent(
            event_name="x",
            surface="s" * 21,
            feature="generator",
            action="invoke",
            status="ok",
        )


def test_event_rejects_overlong_feature():
    with pytest.raises(ValueError):
        TelemetryEvent(
            event_name="x",
            surface="discord",
            feature="f" * 51,
            action="invoke",
            status="ok",
        )
