"""Behaviour tests for alttprbot/services/guild_config.py.

The ``Config`` model is replaced with an in-memory fake that counts queries, so
these run without a database and check both the values returned and that the
cache is filled and cleared when it should be.
"""

import asyncio
import types

import pytest

from alttprbot.services import guild_config


class _Row:
    def __init__(self, guild_id, parameter, value):
        self.guild_id = guild_id
        self.parameter = parameter
        self.value = value


class _Query:
    def __init__(self, store, criteria):
        self._store = store
        self._criteria = criteria

    def _matches(self):
        return [r for r in self._store.rows
                if all(getattr(r, k) == v for k, v in self._criteria.items())]

    def __await__(self):
        self._store.queries += 1

        async def _result():
            return self._matches()
        return _result().__await__()

    async def delete(self):
        for row in self._matches():
            self._store.rows.remove(row)


class _FakeConfig:
    def __init__(self):
        self.rows = []
        self.queries = 0

    async def get_or_none(self, **criteria):
        self.queries += 1
        matches = _Query(self, criteria)._matches()
        return matches[0] if matches else None

    def filter(self, **criteria):
        return _Query(self, criteria)

    async def update_or_create(self, defaults, **criteria):
        matches = _Query(self, criteria)._matches()
        if matches:
            matches[0].value = defaults['value']
        else:
            self.rows.append(_Row(value=defaults['value'], **criteria))


@pytest.fixture
def store(monkeypatch):
    fake = _FakeConfig()
    monkeypatch.setattr(guild_config, "models", types.SimpleNamespace(Config=fake))
    asyncio.run(guild_config.CACHE.clear())
    yield fake
    asyncio.run(guild_config.CACHE.clear())


def run(coro):
    return asyncio.run(coro)


def test_get_returns_stored_value_and_caches_it(store):
    store.rows.append(_Row(1, "CommandPrefix", "!"))

    assert run(guild_config.get(1, "CommandPrefix", "$")) == "!"
    assert run(guild_config.get(1, "CommandPrefix", "$")) == "!"
    assert store.queries == 1


def test_missing_value_returns_callers_default_and_is_cached(store):
    assert run(guild_config.get(1, "CommandPrefix", "$")) == "$"
    # A different default from another caller isn't poisoned by the first one.
    assert run(guild_config.get(1, "CommandPrefix")) is None
    assert store.queries == 1


def test_set_value_clears_every_cached_view(store):
    run(guild_config.get(1, "TournamentEnabled"))
    run(guild_config.for_guild(1))
    run(guild_config.guilds_with("TournamentEnabled"))

    run(guild_config.set_value(1, "TournamentEnabled", "true"))

    assert run(guild_config.is_enabled(1, "TournamentEnabled")) is True
    assert run(guild_config.for_guild(1)) == {"TournamentEnabled": "true"}
    assert run(guild_config.guilds_with("TournamentEnabled")) == {1: "true"}


def test_delete_value(store):
    run(guild_config.set_value(1, "AuditLogging", "true"))
    assert run(guild_config.is_enabled(1, "AuditLogging")) is True

    run(guild_config.delete_value(1, "AuditLogging"))

    assert run(guild_config.is_enabled(1, "AuditLogging")) is False
    assert store.rows == []


def test_settings_are_per_guild(store):
    store.rows.append(_Row(1, "DailyAnnouncerChannel", "daily"))
    store.rows.append(_Row(2, "DailyAnnouncerChannel", "races,daily"))
    store.rows.append(_Row(2, "CommandPrefix", "!"))

    assert run(guild_config.get(3, "DailyAnnouncerChannel")) is None
    assert run(guild_config.guilds_with("DailyAnnouncerChannel")) == {1: "daily", 2: "races,daily"}
    assert run(guild_config.for_guild(2)) == {"DailyAnnouncerChannel": "races,daily", "CommandPrefix": "!"}


def test_get_list_splits_comma_separated_values(store):
    store.rows.append(_Row(1, "Channels", "general, races,,"))

    assert run(guild_config.get_list(1, "Channels")) == ["general", "races"]
    assert run(guild_config.get_list(1, "Unset")) is None

