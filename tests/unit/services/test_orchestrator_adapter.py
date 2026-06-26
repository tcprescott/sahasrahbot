"""Tests for the OrchestratorAdapter's backward-compat surface (cog-facing).

The un-migrated discord cog reads live discord objects + scalar props off the dispatched
object; the adapter resolves the TournamentDefinition into a live TournamentConfig and
exposes the legacy property surface. Here we drive _build_config + the properties with a
fake discordbot.
"""

import alttprbot.tournament.orchestrator_adapter as adapter_mod
from alttprbot.services.tournament import TournamentDefinition
from alttprbot.tournament.orchestrator_adapter import make_adapter


class _Role:
    def __init__(self, rid):
        self.id = rid


class _Guild:
    def __init__(self, roles):
        self._roles = {r: _Role(r) for r in roles}

    def get_role(self, rid):
        return self._roles.get(rid)


class _FakeBot:
    def __init__(self, guild, channels):
        self._guild = guild
        self._channels = channels

    def get_guild(self, gid):
        return self._guild if gid == 555 else None

    def get_channel(self, cid):
        return self._channels.get(cid)


DEFN = TournamentDefinition(
    event_slug="test", racetime_category="test", racetime_goal="Beat the game",
    guild_id=555, audit_channel_id=10, commentary_channel_id=11,
    scheduling_needs_channel_id=None, helper_role_ids=[7, 8, 999],
    stream_delay=10, room_open_time=35, lang="en", submission_form="myform",
    create_scheduled_events=True, scheduling_needs_tracker=True,
)


def _patch_bot(monkeypatch):
    guild = _Guild(roles=[7, 8])  # 999 is not a real role -> dropped
    bot = _FakeBot(guild, channels={10: "AUDIT", 11: "COMMENTARY"})
    monkeypatch.setattr(adapter_mod, "discordbot", bot)
    return guild


def test_build_config_resolves_ids_to_live_objects(monkeypatch):
    guild = _patch_bot(monkeypatch)
    AdapterCls = make_adapter(object, DEFN)
    adapter = AdapterCls()
    cfg = adapter._build_config()

    assert cfg.guild is guild
    assert cfg.audit_channel == "AUDIT"
    assert cfg.commentary_channel == "COMMENTARY"
    assert cfg.scheduling_needs_channel is None  # id was None
    assert [r.id for r in cfg.helper_roles] == [7, 8]  # unknown role 999 dropped
    assert cfg.racetime_category == "test"
    assert cfg.create_scheduled_events is True
    assert cfg.scheduling_needs_tracker is True


def test_cog_facing_properties(monkeypatch):
    _patch_bot(monkeypatch)
    AdapterCls = make_adapter(object, DEFN)
    adapter = AdapterCls()
    adapter.data = adapter._build_config()

    assert adapter.guild is not None
    assert adapter.audit_channel == "AUDIT"
    assert adapter.commentary_channel == "COMMENTARY"
    assert adapter.lang == "en"
    assert adapter.submission_form == "myform"
    assert adapter.hours_before_room_open == (10 + 35) / 60
    # the cog reads .data.racetime_category / .data.scheduling_needs_channel
    assert adapter.data.racetime_category == "test"
    assert adapter.data.scheduling_needs_channel is None


def test_player_racetime_ids_safe_without_orchestrator(monkeypatch):
    _patch_bot(monkeypatch)
    AdapterCls = make_adapter(object, DEFN)
    adapter = AdapterCls()
    assert adapter.player_racetime_ids == []  # orchestrator not built yet
