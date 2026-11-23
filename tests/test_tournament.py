"""Characterization tests for the tournament engine (alttprbot/tournament/).

Discord, racetime.gg and SpeedGaming are faked: a TournamentRace is built by
hand with a SpeedGaming-shaped episode dict, a TournamentConfig whose guild
and channels are mocks, and an rtgg_handler mock that records chat messages.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

import discord
import pytest

import config
from alttprbot import models
from alttprbot.services import bots
from alttprbot.tournament import alttpr_quals, core


def episode(players=("Alice", "Bob"), channels=("ALTTPRandomizer",), **overrides):
    data = {
        "id": 12345,
        "event": {"shortName": "ALTTPR", "slug": "alttpr"},
        "match1": {
            "title": "Round 1",
            "players": [
                {
                    "displayName": name,
                    "publicStream": "",
                    "discordId": str(100 + i),
                    "discordTag": f"{name.lower()}#0",
                    "streamingFrom": f"{name.lower()}_tv",
                }
                for i, name in enumerate(players)
            ],
        },
        "channels": [{"name": c} for c in channels],
        "when": "2024-06-01T20:00:00-04:00",
        "whenCountdown": "2024-06-01T19:50:00-04:00",
    }
    data.update(overrides)
    return data


def player(name, rtgg_id=None):
    p = core.TournamentPlayer()
    p.discord_user = mock.AsyncMock(spec=discord.Member)
    p.discord_user.name = name
    p.data = SimpleNamespace(rtgg_id=rtgg_id or f"rt-{name}")
    return p


def make_race(players=("Alice", "Bob"), cls=core.TournamentRace, **config_kwargs):
    race = cls(episodeid="12345", rtgg_handler=mock.AsyncMock())
    race.episode = episode(players=players)
    race.players = [player(n) for n in players]
    race.tournament_game = None
    race.data = core.TournamentConfig(
        guild=mock.Mock(spec=discord.Guild),
        racetime_category="alttpr",
        racetime_goal="Beat the game",
        event_slug="alttpr",
        audit_channel=mock.AsyncMock(),
        commentary_channel=mock.AsyncMock(),
        **config_kwargs,
    )
    return race


# ---------------------------------------------------------------------------
# TournamentConfig / TournamentRace properties
# ---------------------------------------------------------------------------


def test_tournament_config_defaults():
    cfg = core.TournamentConfig(guild=None, racetime_category="c", racetime_goal="g", event_slug="e")
    assert (cfg.schedule_type, cfg.stream_delay, cfg.room_open_time, cfg.lang, cfg.coop) == ("sg", 0, 35, "en", False)
    assert cfg.gsheet_id == config.TOURNAMENT_RESULTS_SHEET
    assert cfg.auto_record is False and cfg.create_scheduled_events is False


def test_episode_id_is_coerced_to_int_when_possible():
    assert core.TournamentRace(episodeid="42").episodeid == 42
    assert core.TournamentRace(episodeid=None).episodeid is None


def test_race_properties_from_episode():
    race = make_race()
    assert race.event_name == "ALTTPR"
    assert race.event_slug == "alttpr"
    assert race.friendly_name == "Round 1"
    assert race.player_names == ["Alice", "Bob"]
    assert race.player_racetime_ids == ["rt-Alice", "rt-Bob"]
    assert race.player_twitch_names == ["alice_tv", "bob_tv"]
    assert race.versus == "Alice vs. Bob"
    assert race.submit_link == f"{config.APP_URL}/submit/alttpr?episode_id=12345"
    assert race.lang == "en"
    assert race.game_number == ""
    assert race.seed_code is None and race.submission_form is None


def test_versus_with_more_than_two_players_uses_commas():
    assert make_race(players=("A", "B", "C")).versus == "A, B, C"


def test_broadcast_channels_skip_names_with_spaces():
    race = make_race()
    race.episode["channels"] = [{"name": "ALTTPRandomizer"}, {"name": "Not A Channel"}, {"name": "SpeedGaming"}]
    assert race.broadcast_channels == ["ALTTPRandomizer", "SpeedGaming"]
    assert race.broadcast_channel_links == (
        "[ALTTPRandomizer](https://twitch.tv/ALTTPRandomizer), [SpeedGaming](https://twitch.tv/SpeedGaming)"
    )


def test_race_info():
    race = make_race()
    assert race.race_info == "ALTTPR - Alice vs. Bob - Round 1 - Restream(s) at ALTTPRandomizer - 12345"
    race.tournament_game = SimpleNamespace(game_number=3)
    race.episode["channels"] = []
    assert race.race_info == "ALTTPR - Alice vs. Bob - Round 1 - Game #3 - 12345"


def test_start_times_and_eastern_formatting():
    race = make_race()
    assert race.race_start_time == datetime(2024, 6, 1, 23, 50, tzinfo=timezone.utc)
    assert race.race_start_time_restream == datetime(2024, 6, 2, 0, 0, tzinfo=timezone.utc)
    assert race.string_time(race.race_start_time) == "7:50 PM"


def test_hours_before_room_open():
    assert make_race(stream_delay=10, room_open_time=50).hours_before_room_open == 1.0


# ---------------------------------------------------------------------------
# Player lookup
# ---------------------------------------------------------------------------


async def test_tournament_player_construct_by_discord_id(db):
    await models.Users.create(discord_user_id=555, rtgg_id="rt555", display_name="p")
    member = mock.Mock(spec=discord.Member)
    member.name = "pname"
    with mock.patch.object(core.discord_members, "get_member", mock.AsyncMock(return_value=member)) as gm:
        p = await core.TournamentPlayer.construct(discord_id="555", guild="guild")
    gm.assert_awaited_once_with("guild", 555)
    assert p.rtgg_id == "rt555"
    assert p.name == "pname"


async def test_tournament_player_construct_unknown_user_raises(db):
    with pytest.raises(core.UnableToLookupUserException):
        await core.TournamentPlayer.construct(discord_id=1, guild=None)


async def test_tournament_player_construct_by_name_strips_hash_zero(db):
    await models.Users.create(discord_user_id=777, display_name="p")
    member = mock.Mock(spec=discord.Member)
    member.id = 777
    with mock.patch.object(core.discord_members, "get_member_named", mock.AsyncMock(return_value=member)) as gmn:
        p = await core.TournamentPlayer.construct_discord_name("someone#0", guild="guild")
    gmn.assert_awaited_once_with("guild", "someone")
    assert p.discord_user is member


async def test_tournament_player_construct_by_name_errors(db):
    with mock.patch.object(core.discord_members, "get_member_named", mock.AsyncMock(return_value=None)):
        with pytest.raises(core.UnableToLookupUserException, match="Unable to lookup player"):
            await core.TournamentPlayer.construct_discord_name("ghost", guild=None)
    member = mock.Mock(spec=discord.Member)
    member.id = 999
    with mock.patch.object(core.discord_members, "get_member_named", mock.AsyncMock(return_value=member)):
        with pytest.raises(core.UnableToLookupUserException, match="nick data"):
            await core.TournamentPlayer.construct_discord_name("nobody", guild=None)


async def test_make_tournament_player_falls_back_to_discord_tag():
    race = make_race()
    sentinel = object()
    with mock.patch.object(core.TournamentPlayer, "construct", mock.AsyncMock()) as by_id, mock.patch.object(
        core.TournamentPlayer, "construct_discord_name", mock.AsyncMock(return_value=sentinel)
    ) as by_name:
        result = await race.make_tournament_player({"discordId": "", "discordTag": "x#0", "displayName": "X"})
    by_id.assert_not_called()
    by_name.assert_awaited_once()
    assert result is sentinel


async def test_make_tournament_player_with_no_ids_raises():
    race = make_race()
    with pytest.raises(core.UnableToLookupUserException, match="`X`"):
        await race.make_tournament_player({"discordId": "", "discordTag": "", "displayName": "X"})


async def test_update_data_skips_ignored_players(db, monkeypatch):
    race = make_race()
    race.episode["match1"]["players"][1]["publicStream"] = "ignore"
    rtgg_bot = mock.Mock()
    rtgg_bot.get_team = mock.AsyncMock(return_value={"members": []})
    monkeypatch.setattr(bots, "_racetime_bots", {"alttpr": rtgg_bot})
    made = []

    async def fake_make(p):
        made.append(p["displayName"])
        return player(p["displayName"])

    monkeypatch.setattr(race, "make_tournament_player", fake_make)
    await race.update_data(update_episode=False)
    assert made == ["Alice"]
    assert race.rtgg_bot is rtgg_bot


# ---------------------------------------------------------------------------
# can_gatekeep
# ---------------------------------------------------------------------------


async def test_can_gatekeep(db):
    helper_role = object()
    race = make_race(helper_roles=[helper_role])
    race.restream_team = {"members": [{"id": "volunteer"}]}
    await models.Users.create(discord_user_id=1, rtgg_id="helper", display_name="h")
    await models.Users.create(discord_user_id=2, rtgg_id="rando", display_name="r")

    async def get_member(guild, user_id):
        return SimpleNamespace(roles=[helper_role] if user_id == 1 else [])

    with mock.patch.object(core.discord_members, "get_member", get_member):
        assert await race.can_gatekeep("volunteer") is True  # on the SG volunteers team
        assert await race.can_gatekeep("helper") is True  # has a helper role
        assert await race.can_gatekeep("rando") is False
        assert await race.can_gatekeep("unknown") is False


# ---------------------------------------------------------------------------
# Messaging
# ---------------------------------------------------------------------------


async def test_send_audit_and_commentary_messages_publish_events(monkeypatch):
    """Changed when the engine moved onto the event bridge: these publish, and
    alttprbot_discord/notifications.py posts (see tests/test_events.py)."""
    published = []
    monkeypatch.setattr(core.events, "publish", published.append)
    race = make_race()
    race.data.audit_channel.id = 111
    race.data.commentary_channel.id = 222

    await race.send_audit_message("hello")
    embed = discord.Embed(title="x")
    await race.send_commentary_message(embed)
    assert published == [
        core.events.TournamentAuditRecorded(event_slug="alttpr", episode_id=12345, channel_id=111,
                                            content="hello", embed=None),
        core.events.TournamentCommentaryReady(event_slug="alttpr", episode_id=12345, channel_id=222,
                                              embed=embed.to_dict()),
    ]
    race.data.audit_channel.send.assert_not_called()
    race.data.commentary_channel.send.assert_not_called()

    published.clear()
    race.episode["channels"] = []  # no restream, no commentary post
    await race.send_commentary_message(embed)
    assert published == []


async def test_no_audit_channel_publishes_nothing(monkeypatch):
    published = []
    monkeypatch.setattr(core.events, "publish", published.append)
    race = make_race()
    race.data.audit_channel = None
    race.data.commentary_channel = None
    await race.send_audit_message("hello")
    await race.send_commentary_message(discord.Embed(title="x"))
    assert published == []


async def test_publish_settings_submitted(monkeypatch):
    published = []
    monkeypatch.setattr(core.events, "publish", published.append)
    race = make_race()
    race.data.audit_channel.id = 111
    embed = discord.Embed(title="Settings")

    race.publish_settings_submitted(embed)
    [event] = published
    assert event.audit_channel_id == 111
    assert event.episode_id == 12345
    assert event.event_slug == "alttpr"
    assert event.embed == embed.to_dict()
    assert event.players == (
        core.events.TournamentPlayerRef(name="Alice", discord_id=race.players[0].discord_user.id),
        core.events.TournamentPlayerRef(name="Bob", discord_id=race.players[1].discord_user.id),
    )


async def test_send_player_message_without_handler_raises():
    race = make_race()
    race.rtgg_handler = None
    with pytest.raises(core.SahasrahBotException):
        await race.send_player_message("x", None, discord.Embed())


async def test_send_player_message_dm_failure_reports_to_audit_and_room():
    race = make_race()
    member = race.players[0].discord_user
    member.discriminator = "0"
    member.send.side_effect = discord.HTTPException(mock.Mock(status=403), "nope")
    await race.send_player_message("Alice", member, discord.Embed())
    assert "could not send DM to Alice#0" in race.data.audit_channel.send.call_args.args[0]
    race.rtgg_handler.send_message.assert_awaited_once()


async def test_send_player_room_info_publishes_room_opened(monkeypatch):
    """The DMs themselves are sent by alttprbot_discord/notifications.py (tests/test_events.py)."""
    published = []
    monkeypatch.setattr(core.events, "publish", published.append)
    race = make_race()
    race.rtgg_bot = mock.Mock(http_uri=lambda path: f"https://racetime.test{path}")
    race.rtgg_handler.data = {"url": "/alttpr/room", "name": "alttpr/room"}

    await race.send_player_room_info()
    [event] = published
    assert isinstance(event, core.events.TournamentRoomOpened)
    assert event.room_url == "https://racetime.test/alttpr/room"
    assert event.versus == "Alice vs. Bob"
    assert event.player_discord_ids == tuple(p.discord_user.id for p in race.players)
    for player in race.players:
        player.discord_user.send.assert_not_called()


async def test_known_issue_player_without_discord_member_crashes_room_info():
    """KNOWN ISSUE, pinned not endorsed: ``player_discords`` reads
    ``discord_user.name`` before the ``player is None`` check, so a player whose
    Discord member couldn't be found raises AttributeError instead of being skipped."""
    race = make_race()
    race.rtgg_bot = mock.Mock(http_uri=lambda path: path)
    race.rtgg_handler.data = {"url": "/r"}
    race.players[1].discord_user = None
    with pytest.raises(AttributeError):
        await race.send_player_room_info()


class _FormRace(core.TournamentRace):
    @property
    def submission_form(self):
        return "form.html"


async def test_send_race_submission_form(db):
    race = make_race(cls=_FormRace)
    await race.send_race_submission_form()
    for p in race.players:
        msg = p.discord_user.send.call_args.args[0]
        assert msg.startswith("Greetings!") and race.submit_link in msg
    game = await models.TournamentGames.get(episode_id=12345)
    assert (game.event, game.submitted) == ("alttpr", 1)

    # already submitted: no second reminder, unless it's the warning variant
    race.tournament_game = game
    for p in race.players:
        p.discord_user.send.reset_mock()
    await race.send_race_submission_form()
    race.players[0].discord_user.send.assert_not_called()
    await race.send_race_submission_form(warning=True)
    assert "cannot be created" in race.players[0].discord_user.send.call_args.args[0]


async def test_send_race_submission_form_noop_without_form(db):
    race = make_race()
    await race.send_race_submission_form()
    race.players[0].discord_user.send.assert_not_called()
    assert await models.TournamentGames.all().count() == 0


async def test_create_race_room_passes_racetime_options():
    race = make_race(coop=True)
    race.rtgg_bot = mock.AsyncMock()
    handler = await race.create_race_room()
    assert handler is race.rtgg_bot.startrace.return_value
    kwargs = race.rtgg_bot.startrace.call_args.kwargs
    assert kwargs["goal"] == "Beat the game"
    assert kwargs["invitational"] is True and kwargs["team_race"] is True
    assert kwargs["info_user"] == race.race_info


# ---------------------------------------------------------------------------
# ALTTPR qualifier live races (alttpr_quals) — the async tournament's live path
# ---------------------------------------------------------------------------


async def make_live_race(runs_per_pool=1):
    tournament = await models.AsyncTournament.create(
        name="Quals", guild_id=1, channel_id=2, owner_id=3, runs_per_pool=runs_per_pool
    )
    pool = await models.AsyncTournamentPermalinkPool.create(tournament=tournament, name="A", preset="open")
    permalink = await models.AsyncTournamentPermalink.create(pool=pool, url="https://x/1", live_race=True)
    live = await models.AsyncTournamentLiveRace.create(tournament=tournament, pool=pool, episode_id=12345)
    return tournament, pool, permalink, live


def entrant(rtgg_id, name, twitch=None):
    return {"user": {"id": rtgg_id, "name": name, "twitch_name": twitch}}


async def test_write_eligible_async_entrants(db):
    tournament, pool, permalink, live = await make_live_race()
    veteran = await models.Users.create(rtgg_id="vet", display_name="Veteran", twitch_name="old")
    await models.AsyncTournamentRace.create(tournament=tournament, permalink=permalink, user=veteran, status="finished")
    busy = await models.Users.create(rtgg_id="busy", display_name="Busy")
    other_pool = await models.AsyncTournamentPermalinkPool.create(tournament=tournament, name="B")
    other_pl = await models.AsyncTournamentPermalink.create(pool=other_pool, url="https://x/2")
    await models.AsyncTournamentRace.create(tournament=tournament, permalink=other_pl, user=busy, status="in_progress")

    room = {"entrants": [entrant("new", "Newbie", "newtv"), entrant("vet", "Veteran", "newtwitch"), entrant("busy", "Busy")]}
    eligible = await alttpr_quals.write_eligible_async_entrants(live, permalink, room)

    assert eligible == ["Newbie"]  # veteran already ran this pool, busy has an active race
    newbie = await models.Users.get(rtgg_id="new")
    assert newbie.twitch_name == "newtv"
    await veteran.refresh_from_db()
    assert veteran.twitch_name == "newtwitch"  # existing users get their twitch name refreshed
    race = await models.AsyncTournamentRace.get(user=newbie)
    assert (race.status, race.live_race_id, race.thread_id) == ("pending", live.id, None)


async def test_write_eligible_async_entrants_runs_per_pool(db):
    tournament, pool, permalink, live = await make_live_race(runs_per_pool=2)
    vet = await models.Users.create(rtgg_id="vet", display_name="Veteran")
    await models.AsyncTournamentRace.create(tournament=tournament, permalink=permalink, user=vet, status="finished")
    assert await alttpr_quals.write_eligible_async_entrants(live, permalink, {"entrants": [entrant("vet", "Veteran")]}) == [
        "Veteran"
    ]


async def test_process_async_tournament_start(db):
    tournament, pool, permalink, live = await make_live_race()
    joined = await models.Users.create(rtgg_id="joined", display_name="Joined")
    left = await models.Users.create(rtgg_id="left", display_name="Left")
    for u in (joined, left):
        await models.AsyncTournamentRace.create(
            tournament=tournament, permalink=permalink, user=u, status="pending", live_race=live
        )

    names = await alttpr_quals.process_async_tournament_start(
        live, {"started_at": "2024-06-01T23:50:00Z", "entrants": [entrant("joined", "Joined")]}
    )

    assert names == ["Joined"]
    race = await models.AsyncTournamentRace.get(user=joined)
    assert race.status == "in_progress"
    assert race.start_time == datetime(2024, 6, 1, 23, 50, tzinfo=timezone.utc)
    assert not await models.AsyncTournamentRace.filter(user=left).exists()
    await live.refresh_from_db()
    assert live.status == "in_progress"


def quals_race():
    race = make_race(cls=alttpr_quals.ALTTPRQualifierRace)
    race.rtgg_bot = mock.Mock(http_uri=lambda path: f"https://racetime.test{path}")
    race.rtgg_handler.data = {"url": "/alttpr/room", "name": "alttpr/room"}
    race.update_data = mock.AsyncMock()
    return race


async def test_quals_race_info_and_seed_time():
    race = quals_race()
    assert race.seed_time == datetime(2024, 6, 1, 23, 40, tzinfo=timezone.utc)
    assert race.race_info == (
        "ALTTPR Main Tournament Live Qualifier - Round 1 at 7:50 PM Eastern on ALTTPRandomizer"
        " - Seed Distributed and Room Locked at 7:40 PM Eastern - 12345"
    )
    assert race.player_racetime_ids == []


@pytest.mark.parametrize(
    "setup, expected",
    [
        ("none", "No live race found"),
        ("rolled", "already been generated"),
    ],
)
async def test_quals_process_tournament_race_guards(db, setup, expected):
    race = quals_race()
    if setup == "rolled":
        tournament, pool, permalink, live = await make_live_race()
        live.permalink = permalink
        await live.save()
    await race.process_tournament_race([], {"user": {"id": "x"}})
    assert expected in race.rtgg_handler.send_message.call_args.args[0]


async def test_quals_process_tournament_race_requires_mod(db):
    race = quals_race()
    await make_live_race()
    await models.Users.create(rtgg_id="x", display_name="X")
    with mock.patch.object(alttpr_quals.asynctournament_service, "is_async_tournament_user", mock.AsyncMock(return_value=False)):
        await race.process_tournament_race([], {"user": {"id": "x"}})
    assert "Only a mod or admin" in race.rtgg_handler.send_message.call_args.args[0]


async def test_quals_process_tournament_race_rolls_and_registers(db):
    race = quals_race()
    tournament, pool, _, live = await make_live_race()
    await models.Users.create(rtgg_id="mod", display_name="Mod")
    seed = SimpleNamespace(url="https://alttpr.test/h/xyz", code=["A", "B", "C", "D", "E"])
    race.rtgg_handler.data["entrants"] = [entrant("runner", "Runner")]

    with mock.patch.object(alttpr_quals.asynctournament_service, "is_async_tournament_user", mock.AsyncMock(return_value=True)), mock.patch.object(
        alttpr_quals.triforce_text, "generate_with_triforce_text", mock.AsyncMock(return_value=seed)
    ) as gen:
        await race.process_tournament_race([], {"user": {"id": "mod"}})

    gen.assert_awaited_once_with("alttpr2024", "open")
    race.rtgg_handler.set_invitational.assert_awaited_once()
    race.rtgg_handler.set_bot_raceinfo.assert_awaited_once_with("https://alttpr.test/h/xyz - (A/B/C/D/E)")
    assert race.rtgg_handler.seed_rolled is True

    await live.refresh_from_db()
    await live.fetch_related("permalink")
    assert live.racetime_slug == "alttpr/room"
    assert live.permalink.url == seed.url and live.permalink.live_race is True
    result = await models.TournamentResults.get(srl_id="alttpr/room")
    assert (result.episode_id, result.event, result.permalink) == ("12345", "alttpr", seed.url)  # CharField
    assert await models.AsyncTournamentRace.filter(user__rtgg_id="runner", status="pending").exists()
    assert "Eligible entrants for this pool: Runner" in race.rtgg_handler.send_message.call_args.args[0]


async def test_quals_construct_race_room_skips_without_live_race(db):
    assert await alttpr_quals.ALTTPRQualifierRace.construct_race_room(999) is None
