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
        self.webhooks = []
        self.dm_should_raise = False

    def get_emojis(self):
        return ["emoji"]

    async def send_channel_message(
        self, channel_id, content=None, *, embed=None, mention_everyone=False, mention_roles=False
    ):
        self.channel_messages.append((channel_id, content, embed, mention_everyone, mention_roles))

    async def send_dm(self, user_id, content=None, *, embed=None):
        if self.dm_should_raise:
            raise discord.HTTPException(
                response=type("R", (), {"status": 403, "reason": "Forbidden"})(), message="blocked"
            )
        self.dms.append((user_id, content, embed))

    async def send_webhook(self, url, *, content=None, embed=None, username=None):
        self.webhooks.append((url, content, embed, username))


def _definition(**kw):
    base = dict(event_slug="test", racetime_category="alttpr", racetime_goal="Beat the game")
    base.update(kw)
    return TournamentDefinition(**base)


async def test_audit_message_sends_to_audit_channel():
    gw = FakeGateway()
    p = TournamentPresenter(_definition(audit_channel_id=999), gateway=gw)
    await p.send_audit_message("hello")
    assert gw.channel_messages == [(999, "hello", None, False, False)]


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
    assert gw.channel_messages == [(42, None, e, False, False)]


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


async def test_build_race_embeds_inserts_racetime_and_broadcast_fields(monkeypatch):
    async def fake_seed_embed(seed, **kw):
        return discord.Embed(title="public")

    async def fake_tournament_embed(seed, **kw):
        return discord.Embed(title="restream")

    monkeypatch.setattr(presenter_mod, "seed_embed", fake_seed_embed)
    monkeypatch.setattr(presenter_mod, "seed_tournament_embed", fake_tournament_embed)

    gw = FakeGateway()
    p = TournamentPresenter(_definition(), gateway=gw)
    embed, tournament_embed = await p.build_race_embeds(
        SeedResult(seed=object()),
        race_info="Race",
        versus="A vs B",
        room_url="http://rt/room",
        broadcast_channels=["restreamA", "restreamB"],
    )

    # final field order per embed: [Broadcast Channels, RaceTime.gg, ...] (both embeds)
    for e in (embed, tournament_embed):
        assert e.fields[0].name == "Broadcast Channels"
        assert e.fields[0].value == "[restreamA](https://twitch.tv/restreamA), [restreamB](https://twitch.tv/restreamB)"
        assert e.fields[1].name == "RaceTime.gg"
        assert e.fields[1].value == "http://rt/room"


async def test_build_race_embeds_without_broadcasts_only_inserts_racetime(monkeypatch):
    async def fake_seed_embed(seed, **kw):
        return discord.Embed(title="public")

    async def fake_tournament_embed(seed, **kw):
        return discord.Embed(title="restream")

    monkeypatch.setattr(presenter_mod, "seed_embed", fake_seed_embed)
    monkeypatch.setattr(presenter_mod, "seed_tournament_embed", fake_tournament_embed)

    gw = FakeGateway()
    p = TournamentPresenter(_definition(), gateway=gw)
    embed, tournament_embed = await p.build_race_embeds(
        SeedResult(seed=object()), race_info="Race", versus="A vs B",
        room_url="http://rt/room", broadcast_channels=[],
    )
    for e in (embed, tournament_embed):
        assert e.fields[0].name == "RaceTime.gg"
        assert all(f.name != "Broadcast Channels" for f in e.fields)


async def test_send_player_seed_dm_returns_true_on_success():
    gw = FakeGateway()
    p = TournamentPresenter(_definition(), gateway=gw)
    embed = discord.Embed(title="seed")
    assert await p.send_player_seed_dm(123, embed=embed) is True
    assert gw.dms == [(123, None, embed)]


async def test_send_player_seed_dm_returns_false_for_unresolved_member():
    gw = FakeGateway()
    p = TournamentPresenter(_definition(), gateway=gw)
    assert await p.send_player_seed_dm(None, embed=discord.Embed(title="seed")) is False
    assert gw.dms == []  # no send attempted


async def test_send_player_seed_dm_returns_false_on_http_exception():
    gw = FakeGateway()
    gw.dm_should_raise = True
    p = TournamentPresenter(_definition(), gateway=gw)
    assert await p.send_player_seed_dm(123, embed=discord.Embed(title="seed")) is False


async def test_send_audit_alert_mentions_everyone():
    gw = FakeGateway()
    p = TournamentPresenter(_definition(audit_channel_id=999), gateway=gw)
    await p.send_audit_alert("@here could not send DM to A")
    assert gw.channel_messages == [(999, "@here could not send DM to A", None, True, False)]


async def test_send_audit_alert_noop_without_channel():
    gw = FakeGateway()
    p = TournamentPresenter(_definition(), gateway=gw)
    await p.send_audit_alert("@here could not send DM to A")
    assert gw.channel_messages == []


# --- submission flow (PR6) ---

async def test_send_player_reminders_dms_resolved_players_and_propagates():
    gw = FakeGateway()
    p = TournamentPresenter(_definition(), gateway=gw)
    await p.send_player_reminders([1, None, 2], "please submit")
    assert gw.dms == [(1, "please submit", None), (2, "please submit", None)]  # None skipped

    gw.dm_should_raise = True  # reminders do NOT swallow failures (cog wraps the call)
    with pytest.raises(discord.HTTPException):
        await p.send_player_reminders([3], "please submit")


async def test_send_submission_confirmation_posts_audit_and_dms():
    gw = FakeGateway()
    p = TournamentPresenter(_definition(audit_channel_id=77), gateway=gw)
    await p.send_submission_confirmation(
        versus="A vs B", episode_id=100, event="smrl", game_number=2,
        randomizer="smdash", preset="recall_mm", submitted_by="user",
        players=[("A", 1), ("B", 2)],
    )
    # audit embed first, then a DM per player
    assert gw.channel_messages[0][0] == 77 and gw.channel_messages[0][3] is False
    audit_embed = gw.channel_messages[0][2]
    assert audit_embed.title == "SMRL - A vs B"
    field_names = [f.name for f in audit_embed.fields]
    assert field_names == ["Episode ID", "Event", "Game #", "Randomizer", "Preset", "Submitted by"]
    assert [d[0] for d in gw.dms] == [1, 2]


async def test_send_submission_confirmation_alerts_on_unresolved_and_failed_dm():
    gw = FakeGateway()
    p = TournamentPresenter(_definition(audit_channel_id=77), gateway=gw)
    gw.dm_should_raise = True  # both DMs fail -> @here alerts (carrying the embed)
    await p.send_submission_confirmation(
        versus="A vs B", episode_id=100, event="smrl", game_number=1,
        randomizer="smvaria", preset="RLS4W5", submitted_by="user",
        players=[("A", None), ("B", 2)],
    )
    # 1 audit embed + 2 @here alerts (one for unresolved A, one for failed-DM B)
    alerts = [m for m in gw.channel_messages if m[3] is True]
    assert len(alerts) == 2
    assert all(a[2] is not None for a in alerts)  # each alert carries the embed
    assert {a[1] for a in alerts} == {"@here could not send DM to A", "@here could not send DM to B"}


# --- open-race announcement (PR7) ---

import datetime  # noqa: E402

_START = datetime.datetime(2026, 6, 26, 18, 0, tzinfo=datetime.timezone.utc)
_SEED = _START - datetime.timedelta(minutes=10)


async def test_send_race_announcement_alttpr_daily_with_seed_and_webhook():
    gw = FakeGateway()
    p = TournamentPresenter(_definition(), gateway=gw)
    await p.send_race_announcement(
        555,
        prefix="",
        series="SpeedGaming Daily Race Series",
        title="Daily 1",
        race_start_time=_START,
        broadcast_channels=["restreamA"],
        room_url="http://rt/room",
        seed_time=_SEED,
        webhook_url="http://hook",
        webhook_role_mention="<@&399038388964950016>",
    )
    cid, content, embed, m_everyone, m_roles = gw.channel_messages[0]
    assert cid == 555 and m_roles is True and m_everyone is False
    assert content.startswith("SpeedGaming Daily Race Series - Daily 1 - ")
    assert " on restreamA" in content
    assert "Seed Distributed " in content and content.endswith(" - http://rt/room")
    # webhook gets the same message prefixed with the role mention + the SahasrahBot username
    assert len(gw.webhooks) == 1
    url, wh_content, _, username = gw.webhooks[0]
    assert url == "http://hook" and username == "SahasrahBot"
    assert wh_content == f"<@&399038388964950016> {content}"


async def test_send_race_announcement_smz3_prefix_no_seed_no_webhook():
    gw = FakeGateway()
    p = TournamentPresenter(_definition(), gateway=gw)
    await p.send_race_announcement(
        777,
        prefix="<@&449260882501959700> ",
        series="SMZ3 Weekly Race",
        title="Weekly 1",
        race_start_time=_START,
        broadcast_channels=[],
        room_url="http://rt/smz3",
        seed_time=None,
    )
    cid, content, _, _, m_roles = gw.channel_messages[0]
    assert cid == 777 and m_roles is True
    assert content.startswith("<@&449260882501959700> SMZ3 Weekly Race - Weekly 1 - ")
    assert "Seed Distributed" not in content
    assert content.endswith(" - http://rt/smz3")
    assert " on " not in content  # no broadcast channels
    assert gw.webhooks == []  # no webhook for smz3
