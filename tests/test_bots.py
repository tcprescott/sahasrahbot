"""alttprbot.services.bots: how core code reaches the live Discord and racetime bots.

The front ends register their singletons at startup (sahasrahbot.py), so core code
never imports them. These tests pin the lookup behaviour and that each front end's
``register()`` hands over the real singleton.
"""

from types import SimpleNamespace

import pytest

from alttprbot.services import bots


@pytest.fixture
def unregistered(monkeypatch):
    monkeypatch.setattr(bots, "_discord_client", None)
    monkeypatch.setattr(bots, "_racetime_bots", None)


def test_discord_raises_until_registered(unregistered):
    with pytest.raises(RuntimeError, match="No Discord client registered"):
        bots.discord()


def test_racetime_bots_raise_until_registered(unregistered):
    with pytest.raises(RuntimeError, match="No racetime bots registered"):
        bots.racetime_bots()
    with pytest.raises(RuntimeError):
        bots.racetime_bot("alttpr")


def test_set_and_get(unregistered):
    client = SimpleNamespace()
    mapping = {"alttpr": SimpleNamespace()}
    bots.set_discord_client(client)
    bots.set_racetime_bots(mapping)
    assert bots.discord() is client
    assert bots.racetime_bots() is mapping
    assert bots.racetime_bot("alttpr") is mapping["alttpr"]


def test_racetime_mapping_is_kept_by_reference(unregistered):
    mapping = {}
    bots.set_racetime_bots(mapping)
    later = SimpleNamespace()
    mapping["smz3"] = later
    assert bots.racetime_bot("smz3") is later


def test_unknown_racetime_category_is_a_key_error(unregistered):
    # Same as the old ``racetime_bots[category]`` lookup the engine used.
    bots.set_racetime_bots({})
    with pytest.raises(KeyError):
        bots.racetime_bot("nope")


def test_discord_gateways_register_the_real_bot(unregistered, monkeypatch):
    from alttprbot.services import asynctournament, asynctournament_jobs
    from alttprbot.util import seed_presenter
    from alttprbot_discord import gateways
    from alttprbot_discord.bot import discordbot

    # register() also wires other services; keep those globals as they were.
    monkeypatch.setattr(asynctournament, "set_member_role_lookup", lambda fn: None)
    monkeypatch.setattr(asynctournament_jobs, "set_timeout_notifier", lambda fn: None)
    monkeypatch.setattr(seed_presenter, "register", lambda *a: None)

    gateways.register()
    assert bots.discord() is discordbot


def test_racetime_gateways_register_the_real_bots(unregistered):
    from alttprbot_racetime import gateways
    from alttprbot_racetime.bot import racetime_bots

    gateways.register()
    assert bots.racetime_bots() is racetime_bots
