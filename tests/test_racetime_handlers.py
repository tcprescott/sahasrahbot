"""Characterization tests for the racetime.gg race handlers (alttprbot_racetime/).

Handlers are built with a mock websocket and their outgoing actions
(send_message, set_bot_raceinfo, accept_request, ...) replaced by AsyncMocks,
so a test can feed a chat message through ``chat_message`` the way racetime.gg
would and assert what the bot said and did. Seed generation is faked.
"""

import asyncio
import importlib
import logging
import pkgutil
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

import pytest

import alttprbot_racetime.handlers as handlers_pkg
from alttprbot import models
from alttprbot.alttprgen import generator
from alttprbot_racetime import config as rt_config
from alttprbot_racetime.handlers import alttpr, core, ctjets, smz3

ACTIONS = (
    "send_message",
    "set_bot_raceinfo",
    "accept_request",
    "add_monitor",
    "edit",
    "set_invitational",
    "invite_user",
)


def make_handler(cls=core.SahasrahBotCoreHandler, data=None, state=None):
    h = cls(logger=logging.getLogger("test"), conn=mock.AsyncMock(), bot=mock.Mock(category_slug="alttpr"), state=state if state is not None else {})
    for name in ACTIONS:
        setattr(h, name, mock.AsyncMock())
    h.data = data or {"name": "alttpr/cool-room-1234", "category": {"slug": "alttpr"}, "entrants": []}
    return h


def said(h):
    return [c.args[0] for c in h.send_message.call_args_list]


async def chat(h, text, user_id="u1", monitor=False):
    await h.chat_message({"message": {"message": text, "user": {"id": user_id}, "is_monitor": monitor}})


def fake_seed():
    return SimpleNamespace(url="https://alttpr.test/h/abc", code=["Bow", "Bombs", "Hookshot", "Lamp", "Map"], hash="abc")


# ---------------------------------------------------------------------------
# Category map
# ---------------------------------------------------------------------------


def test_racetime_bot_config_reads_client_credentials_from_config(monkeypatch):
    import config

    monkeypatch.setattr(config, "RACETIME_CLIENT_ID_CTJETS", "id-x", raising=False)
    monkeypatch.setattr(config, "RACETIME_CLIENT_SECRET_CTJETS", "secret-x", raising=False)
    cfg = rt_config.RacetimeBotConfig(category_slug="ct-jets", handler_class=ctjets.GameHandler)
    assert (cfg.client_id, cfg.client_secret) == ("id-x", "secret-x")


def test_every_handler_module_defines_a_core_handler_subclass():
    for info in pkgutil.iter_modules(handlers_pkg.__path__):
        if info.name == "core":
            continue
        module = importlib.import_module(f"alttprbot_racetime.handlers.{info.name}")
        assert issubclass(module.GameHandler, core.SahasrahBotCoreHandler), info.name


@pytest.mark.parametrize(
    "module", [m.name for m in pkgutil.iter_modules(handlers_pkg.__path__) if m.name != "core"]
)
async def test_help_command_replies_where_defined(module):
    cls = importlib.import_module(f"alttprbot_racetime.handlers.{module}").GameHandler
    if not hasattr(cls, "ex_help"):
        pytest.skip("no !help")
    h = make_handler(cls)
    await chat(h, "!help")
    if module == "twwr":
        assert said(h) == []  # twwr deliberately silences !help, !lock and !unlock
        return
    assert said(h) and "Command raised exception" not in said(h)[0]


# ---------------------------------------------------------------------------
# Core handler: locking, teams, state
# ---------------------------------------------------------------------------


async def test_lock_and_unlock_are_monitor_only():
    h = make_handler()
    await chat(h, "!lock")
    assert "only race monitors" in said(h)[0]
    assert not h.state.get("locked")

    await chat(h, "!lock", monitor=True)
    assert h.state["locked"] is True
    await chat(h, "!unlock", monitor=True)
    assert h.state["locked"] is False


async def test_is_locked():
    h = make_handler()
    assert await h.is_locked({}) is False

    h.state["locked"] = True
    assert await h.is_locked({"is_monitor": False}) is True
    assert "locked" in said(h)[-1]
    assert await h.is_locked({"is_monitor": True}) is False

    h.seed_rolled = True
    assert await h.is_locked({"is_monitor": True}) is True
    assert "already rolled a seed" in said(h)[-1]


async def test_bot_and_system_messages_are_ignored():
    h = make_handler()
    await h.chat_message({"message": {"message": "!lock", "is_bot": True, "is_monitor": True}})
    await h.chat_message({"message": {"message": "!lock", "is_system": True, "is_monitor": True}})
    assert not h.state.get("locked")


def test_teams_and_equal_teams():
    h = make_handler(data={
        "team_race": True,
        "entrants": [
            {"user": {"name": "a"}, "team": {"name": "red"}},
            {"user": {"name": "b"}, "team": {"name": "blue"}},
            {"user": {"name": "c"}, "team": {"name": "red"}},
        ],
    })
    assert h.teams == {"blue": ["b"], "red": ["a", "c"]}
    assert h.is_equal_teams is False

    h.data["entrants"].append({"user": {"name": "d"}, "team": {"name": "blue"}})
    assert h.is_equal_teams is True


def test_teams_on_solo_race_raises():
    with pytest.raises(Exception, match="not a team race"):
        make_handler(data={"team_race": False, "entrants": []}).teams


async def test_intro_sent_once():
    h = make_handler()
    await h.intro()
    await h.intro()
    assert len(said(h)) == 1 and "SahasrahBot" in said(h)[0]


async def test_core_cancel_resets_seed_state():
    h = make_handler()
    h.seed_rolled = True
    await chat(h, "!cancel")
    assert h.seed_rolled is False
    h.set_bot_raceinfo.assert_awaited_once_with("New Race")


async def test_tournamentrace_requires_entrant_or_monitor():
    h = make_handler()
    h.data["entrants"] = [{"user": {"id": "runner"}, "status": {"value": "ready"}}, {"user": {"id": "req"}, "status": {"value": "requested"}}]
    await chat(h, "!tournamentrace", user_id="stranger")
    assert "Only entrants or race monitors" in said(h)[-1]
    await chat(h, "!tournamentrace", user_id="req")  # a pending join request doesn't count
    assert "Only entrants or race monitors" in said(h)[-1]

    await chat(h, "!tournamentrace", user_id="runner")
    assert "not associated with a tournament" in said(h)[-1]

    h.tournament = mock.AsyncMock()
    await chat(h, "!tournamentrace", monitor=True, user_id="mod")
    h.tournament.process_tournament_race.assert_awaited_once()


async def test_override_requires_unexpired_whitelist(db):
    h = make_handler()
    h.override_stream = mock.AsyncMock()

    await chat(h, "!override", user_id="nobody")
    assert "do not have permission" in said(h)[-1]

    await models.RTGGOverrideWhitelist.create(racetime_id="ok", category="alttpr", expires=None)
    await chat(h, "!override", user_id="ok")
    h.override_stream.assert_awaited_once_with("ok")


async def test_override_with_expired_whitelist_is_refused(db):
    """``expires`` comes back timezone-aware (``use_tz=True``), so the check
    compares it with an aware "now". It used to compare with naive
    ``utcnow()`` and crash with a TypeError."""
    h = make_handler()
    h.override_stream = mock.AsyncMock()
    await models.RTGGOverrideWhitelist.create(
        racetime_id="old", category="alttpr", expires=datetime.now(timezone.utc) - timedelta(days=1))
    await chat(h, "!override", user_id="old")
    assert said(h)[-1].startswith("Your streaming exemption has expired.")
    h.override_stream.assert_not_called()


async def test_override_with_future_expiry_is_allowed(db):
    h = make_handler()
    h.override_stream = mock.AsyncMock()
    await models.RTGGOverrideWhitelist.create(
        racetime_id="soon", category="alttpr", expires=datetime.now(timezone.utc) + timedelta(days=1))
    await chat(h, "!override", user_id="soon")
    h.override_stream.assert_awaited_once_with("soon")


async def test_override_stream_sends_websocket_action():
    h = make_handler()
    await h.override_stream("user-hash")
    h.ws.send_json.assert_awaited_once_with({"action": "override_stream", "data": {"user": "user-hash"}})


async def test_error_relays_errors_to_chat():
    h = make_handler()
    await h.error({"errors": ["bad", "worse"]})
    assert said(h) == ["Command raised exception: bad,worse"]


# ---------------------------------------------------------------------------
# race_data: status events, tournament gatekeeping, unlisted rooms
# ---------------------------------------------------------------------------


def race_payload(status="open", unlisted=False, entrants=None):
    return {"race": {"name": "alttpr/cool-room-1234", "status": {"value": status}, "unlisted": unlisted, "entrants": entrants or []}}


async def test_race_data_fires_status_handler_only_on_change(db, monkeypatch):
    published = []
    monkeypatch.setattr(core.events, "publish", published.append)
    h = make_handler()
    h.status_pending = mock.AsyncMock()

    await h.race_data(race_payload("open"))  # first update only records the status
    await h.race_data(race_payload("open"))
    h.status_pending.assert_not_called()

    await h.race_data(race_payload("pending"))
    h.status_pending.assert_awaited_once()
    assert [(type(e).__name__, e.status, e.room_name) for e in published] == [
        ("RaceStatusChanged", "pending", "alttpr/cool-room-1234")]


async def test_race_data_tracks_unlisted_rooms(db):
    h = make_handler()
    h.bot.category_slug = "alttpr"
    await h.race_data(race_payload(unlisted=True))
    room = await models.RTGGUnlistedRooms.get(room_name="alttpr/cool-room-1234")
    assert room.category == "alttpr"

    await h.race_data(race_payload(unlisted=False))
    assert not await models.RTGGUnlistedRooms.exists()


async def test_race_data_accepts_tournament_players_and_promotes_gatekeepers(db):
    h = make_handler()
    h.tournament = mock.Mock(player_racetime_ids=["player"])
    h.tournament.can_gatekeep = mock.AsyncMock(side_effect=lambda rid: rid == "helper")
    entrants = [
        {"user": {"id": "player"}, "status": {"value": "requested"}},
        {"user": {"id": "helper"}, "status": {"value": "requested"}},
        {"user": {"id": "rando"}, "status": {"value": "requested"}},
        {"user": {"id": "already"}, "status": {"value": "ready"}},
    ]
    await h.race_data(race_payload(entrants=entrants))
    assert [c.args[0] for c in h.accept_request.call_args_list] == ["player", "helper"]
    h.add_monitor.assert_awaited_once_with("helper")


async def test_status_in_progress_starts_tournament(db):
    h = make_handler()
    h.tournament = mock.AsyncMock()
    await h.status_in_progress()
    h.tournament.on_race_start.assert_awaited_once()


# ---------------------------------------------------------------------------
# Spoiler races
# ---------------------------------------------------------------------------


async def test_schedule_and_delete_spoiler_race(db):
    h = make_handler()
    await h.schedule_spoiler_race("https://spoilers.test/a", 600)
    await h.schedule_spoiler_race("https://spoilers.test/b", 900)  # replaces, doesn't duplicate
    race = await models.SpoilerRaces.get(srl_id="alttpr/cool-room-1234")
    assert (race.spoiler_url, race.studytime) == ("https://spoilers.test/b", 900)

    await h.delete_spoiler_race()
    assert h.spoiler_race is None
    assert not await models.SpoilerRaces.exists()


async def test_send_spoiler_log_posts_url_and_starts_countdown(db):
    h = make_handler()
    await h.schedule_spoiler_race("https://spoilers.test/a", 600)
    h.countdown_timer = mock.AsyncMock()
    await h.send_spoiler_log()
    await asyncio.sleep(0)  # let the background countdown task start
    assert "This race's spoiler log: https://spoilers.test/a" in said(h)
    h.countdown_timer.assert_awaited_once_with(duration_in_seconds=600, beginmessage=True)
    assert (await models.SpoilerRaces.get()).started is not None


async def test_send_spoiler_log_without_spoiler_race_is_noop():
    h = make_handler()
    await h.send_spoiler_log()
    assert said(h) == []


async def test_countdown_timer_short_duration_announces_and_finishes():
    h = make_handler()
    await h.countdown_timer(duration_in_seconds=1.05, beginmessage=True)
    assert said(h)[-1] == "Log study has finished.  Begin racing!"


# ---------------------------------------------------------------------------
# ALTTPR handler commands
# ---------------------------------------------------------------------------


@pytest.fixture
def alttpr_generate(monkeypatch):
    gen = mock.AsyncMock(return_value=fake_seed())
    monkeypatch.setattr(generator.ALTTPRPreset, "generate", gen)
    return gen


async def test_alttpr_intro_offers_roll_action_but_not_in_bot_opened_rooms():
    h = make_handler(alttpr.GameHandler)
    await h.intro()
    assert "actions" in h.send_message.call_args.kwargs

    h2 = make_handler(alttpr.GameHandler)
    h2.data["opened_by_bot"] = "sahasrahbot"
    await h2.intro()
    h2.send_message.assert_not_called()


async def test_alttpr_race_without_preset():
    h = make_handler(alttpr.GameHandler)
    await chat(h, "!race")
    assert said(h) == ["You must specify a preset!"]


async def test_alttpr_race_rolls_seed(alttpr_generate):
    h = make_handler(alttpr.GameHandler)
    await chat(h, "!race open tournament")
    alttpr_generate.assert_awaited_once()
    assert alttpr_generate.call_args.kwargs["branch"] == "tournament"
    assert alttpr_generate.call_args.kwargs["allow_quickswap"] is True
    h.set_bot_raceinfo.assert_awaited_once_with("open - https://alttpr.test/h/abc - (Bow/Bombs/Hookshot/Lamp/Map)")
    assert h.seed_rolled is True

    await chat(h, "!race open")  # second roll is refused
    assert alttpr_generate.await_count == 1
    assert "already rolled" in said(h)[-1]


async def test_alttpr_noqsrace_disables_quickswap(alttpr_generate):
    h = make_handler(alttpr.GameHandler)
    await chat(h, "!noqsrace open")
    assert alttpr_generate.call_args.kwargs["allow_quickswap"] is False
    assert alttpr_generate.call_args.kwargs["branch"] == "live"


async def test_alttpr_missing_preset_reports_error():
    h = make_handler(alttpr.GameHandler)
    await chat(h, "!race doesnotexist")
    assert "Could not find preset doesnotexist" in said(h)[-1]
    assert h.seed_rolled is False


async def test_alttpr_newrace_keyword_args(alttpr_generate):
    h = make_handler(alttpr.GameHandler)
    await chat(h, "!newrace --preset=open --branch=beeta --hints --festive")
    kwargs = alttpr_generate.call_args.kwargs
    assert kwargs["branch"] == "beeta"
    assert kwargs["hints"] is True
    assert kwargs["endpoint_prefix"] == "/festive"
    assert h.seed_rolled is True


async def test_alttpr_newrace_positional_preset(alttpr_generate):
    h = make_handler(alttpr.GameHandler)
    await chat(h, "!newrace open")
    assert alttpr_generate.call_args.kwargs["branch"] == "live"


async def test_alttpr_newrace_spoiler_race_schedules_spoiler(db, monkeypatch):
    spoiler = SimpleNamespace(seed=fake_seed(), spoiler_log_url="https://spoilers.test/x", preset=None)
    gen = mock.AsyncMock(return_value=spoiler)
    monkeypatch.setattr(alttpr.spoilers, "generate_spoiler_game", gen)
    h = make_handler(alttpr.GameHandler)
    await chat(h, "!newrace --preset=open --spoiler_race --countdown=300")
    assert gen.call_args.args == ("open",)
    race = await models.SpoilerRaces.get()
    assert (race.spoiler_url, race.studytime) == ("https://spoilers.test/x", 300)


async def test_alttpr_cancel_is_monitor_only_and_clears_spoiler(db):
    h = make_handler(alttpr.GameHandler)
    h.seed_rolled = True
    await chat(h, "!cancel")
    assert h.seed_rolled is True
    await h.schedule_spoiler_race("x", 1)
    await chat(h, "!cancel", monitor=True)
    assert h.seed_rolled is False
    assert not await models.SpoilerRaces.exists()


async def test_alttpr_mystery_sets_race_info_with_instructions(monkeypatch):
    mystery = SimpleNamespace(seed=fake_seed(), custom_instructions="Play blindfolded")
    gen = mock.AsyncMock(return_value=mystery)
    monkeypatch.setattr(generator.ALTTPRMystery, "generate", gen)
    h = make_handler(alttpr.GameHandler)
    await chat(h, "!mystery")
    assert "Instructions: Play blindfolded" in said(h)
    assert h.set_bot_raceinfo.call_args.args[0].startswith("Instructions: Play blindfolded - mystery weighted - ")


# ---------------------------------------------------------------------------
# SMZ3 and CT Jets handlers
# ---------------------------------------------------------------------------


async def test_smz3_race_rolls_preset(monkeypatch):
    async def fake_generate(self, tournament=True, spoilers=False):
        self.seed = SimpleNamespace(url="https://samus.test/seed/1", code="Abc Def")
        return self.seed

    monkeypatch.setattr(generator.SMZ3Preset, "generate", fake_generate)
    h = make_handler(smz3.GameHandler)
    await chat(h, "!race normal")
    h.set_bot_raceinfo.assert_awaited_once_with("normal - https://samus.test/seed/1 - (Abc Def)")
    assert h.seed_rolled is True


async def test_smz3_multiworld_requires_equal_team_race():
    h = make_handler(smz3.GameHandler)
    h.data["team_race"] = False
    await chat(h, "!multiworld normal")
    assert said(h)[-1] == "This must be a team race."

    h.data.update(team_race=True, entrants=[
        {"user": {"name": "a"}, "team": {"name": "red"}},
        {"user": {"name": "b"}, "team": {"name": "red"}},
        {"user": {"name": "c"}, "team": {"name": "blue"}},
    ])
    await chat(h, "!multiworld normal")
    assert said(h)[-1] == "Teams are unequal in size."


async def test_smz3_multiworld_rejects_out_of_range_seed_number():
    h = make_handler(smz3.GameHandler)
    await chat(h, "!multiworld normal -5")
    assert "Seed number must be between" in said(h)[-1]


async def test_ctjets_preset(monkeypatch):
    monkeypatch.setattr(generator.CTJetsPreset, "generate", mock.AsyncMock(return_value="https://ctjets.test/1"))
    h = make_handler(ctjets.GameHandler)
    await chat(h, "!preset race")
    assert said(h)[1] == "https://ctjets.test/1"
    h.set_bot_raceinfo.assert_awaited_once_with("https://ctjets.test/1")
