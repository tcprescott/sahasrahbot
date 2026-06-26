"""Unit tests for the tournament decomposition value objects."""

from alttprbot.services.tournament import SeedResult, TournamentDefinition


def test_definition_required_and_defaults():
    d = TournamentDefinition(event_slug="test", racetime_category="alttpr", racetime_goal="Beat the game")
    assert d.event_slug == "test"
    assert d.schedule_type == "sg"
    assert d.coop is False
    assert d.room_open_time == 35
    # mutable defaults are independent per instance
    d.helper_role_ids.append(1)
    assert TournamentDefinition("x", "y", "z").helper_role_ids == []


def test_definition_carries_ids_not_objects():
    d = TournamentDefinition(
        event_slug="alttpr", racetime_category="alttpr", racetime_goal="Beat the game",
        guild_id=123, audit_channel_id=456, helper_role_ids=[7, 8], announce_role_id=9,
        webhook_urls={"sg": "http://hook"},
    )
    assert d.guild_id == 123
    assert d.audit_channel_id == 456
    assert d.helper_role_ids == [7, 8]
    assert d.webhook_urls["sg"] == "http://hook"


class _FakeSeed:
    url = "http://seed/permalink"
    code = ["Bow", "Bombs"]


def test_seed_result_url_falls_back_to_seed():
    r = SeedResult(seed=_FakeSeed())
    assert r.url == "http://seed/permalink"
    assert r.code == ["Bow", "Bombs"]


def test_seed_result_permalink_overrides_seed_url():
    r = SeedResult(seed=_FakeSeed(), permalink="http://override", preset="open", spoiler_url="http://spoiler")
    assert r.url == "http://override"
    assert r.preset == "open"
    assert r.spoiler_url == "http://spoiler"
