"""Unit tests for the TournamentPresenter (mock gateway; no live Discord)."""

import discord
import pytest

import alttprbot.presentation.discord.tournament.presenter as presenter_mod
from alttprbot.presentation.discord.tournament import TournamentPresenter
from alttprbot.services.tournament import SeedResult, TournamentDefinition


class FakeGateway:
    def __init__(self):
        self.channel_messages = []
        self.dms = []
        self.dm_should_raise = False

    def get_emojis(self):
        return ["emoji"]

    async def send_channel_message(self, channel_id, content=None, *, embed=None):
        self.channel_messages.append((channel_id, content, embed))

    async def send_dm(self, user_id, content=None, *, embed=None):
        if self.dm_should_raise:
            raise discord.HTTPException(
                response=type("R", (), {"status": 403, "reason": "Forbidden"})(), message="blocked"
            )
        self.dms.append((user_id, content, embed))


def _definition(**kw):
    base = dict(event_slug="test", racetime_category="alttpr", racetime_goal="Beat the game")
    base.update(kw)
    return TournamentDefinition(**base)


async def test_audit_message_sends_to_audit_channel():
    gw = FakeGateway()
    p = TournamentPresenter(_definition(audit_channel_id=999), gateway=gw)
    await p.send_audit_message("hello")
    assert gw.channel_messages == [(999, "hello", None)]


async def test_audit_message_noop_without_channel():
    gw = FakeGateway()
    p = TournamentPresenter(_definition(), gateway=gw)  # no audit_channel_id
    await p.send_audit_message("hello")
    assert gw.channel_messages == []


async def test_commentary_requires_broadcasts_and_channel():
    gw = FakeGateway()
    p = TournamentPresenter(_definition(commentary_channel_id=42), gateway=gw)
    e = discord.Embed(title="x")
    await p.send_commentary_message(e, has_broadcasts=False)
    assert gw.channel_messages == []  # no broadcasts -> skipped
    await p.send_commentary_message(e, has_broadcasts=True)
    assert gw.channel_messages == [(42, None, e)]


async def test_send_player_room_info_dms_each_player_and_survives_failures():
    gw = FakeGateway()
    p = TournamentPresenter(_definition(), gateway=gw)
    await p.send_player_room_info([1, None, 2], versus="A vs B", room_url="http://rt/room")
    assert [d[0] for d in gw.dms] == [1, 2]  # None skipped
    embed = gw.dms[0][2]
    assert "A vs B" in embed.title and "http://rt/room" in embed.description

    gw.dm_should_raise = True  # HTTPException must be swallowed
    await p.send_player_room_info([3], versus="C vs D", room_url="http://rt/room2")


async def test_build_seed_embeds_uses_gateway_emojis(monkeypatch):
    calls = {}

    async def fake_seed_embed(seed, **kw):
        calls["embed"] = kw
        return discord.Embed(title="public")

    async def fake_tournament_embed(seed, **kw):
        calls["tournament"] = kw
        return discord.Embed(title="restream")

    monkeypatch.setattr(presenter_mod, "seed_embed", fake_seed_embed)
    monkeypatch.setattr(presenter_mod, "seed_tournament_embed", fake_tournament_embed)

    gw = FakeGateway()
    p = TournamentPresenter(_definition(), gateway=gw)
    result = SeedResult(seed=object())
    embed, tournament_embed = await p.build_seed_embeds(result, race_info="Race", versus="A vs B")

    assert embed.title == "public" and tournament_embed.title == "restream"
    assert calls["embed"]["emojis"] == ["emoji"]
    assert calls["embed"]["name"] == "Race" and calls["embed"]["notes"] == "A vs B"
