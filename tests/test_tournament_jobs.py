"""The scheduled tournament jobs (alttprbot/services/tournament_jobs.py).

SpeedGaming, the tournament classes and the Discord member lookups are fakes;
published events are captured instead of delivered. ``scheduling_needs`` itself
is covered in ``tests/test_scheduler.py``.
"""

from types import SimpleNamespace
from unittest import mock

import pytest

from alttprbot import events
from alttprbot.services import tournament_jobs as jobs


@pytest.fixture
def published(monkeypatch):
    seen = []
    monkeypatch.setattr(jobs.events, "publish", seen.append)
    return seen


def tournament(**config):
    data = SimpleNamespace(create_scheduled_events=config.pop("create_scheduled_events", False),
                           scheduling_needs_channel=config.pop("scheduling_needs_channel", None),
                           scheduling_needs_tracker=config.pop("scheduling_needs_tracker", False))
    event_config = SimpleNamespace(hours_before_room_open=config.pop("hours_before_room_open", 1),
                                   submission_form=config.pop("submission_form", None), lang="en",
                                   guild=config.pop("guild", None), data=data)
    return SimpleNamespace(get_config=mock.AsyncMock(return_value=event_config), **config)


@pytest.fixture
def schedule(monkeypatch):
    """SpeedGaming episodes by event slug; an Exception value is raised instead."""
    by_event = {}

    async def get(event, hours_past, hours_future):
        result = by_event[event]
        if isinstance(result, Exception):
            raise result
        return result

    fake = mock.AsyncMock(side_effect=get)
    monkeypatch.setattr(jobs.speedgaming, "get_upcoming_episodes_by_event", fake)
    fake.by_event = by_event
    return fake


async def test_create_races_opens_rooms_and_reports_failures(monkeypatch, published, schedule, caplog):
    monkeypatch.setattr(jobs.tournaments, "TOURNAMENT_DATA", {
        "alttpr": tournament(hours_before_room_open=2),
        "down": tournament(),
    })
    schedule.by_event.update(alttpr=[{"id": 1}, {"id": "2"}], down=RuntimeError("SG is down"))

    async def create(event, episode_id):
        if episode_id == "2":
            raise ValueError("no players")

    create_room = mock.AsyncMock(side_effect=create)
    monkeypatch.setattr(jobs, "create_tournament_race_room", create_room)

    await jobs.create_races()

    schedule.assert_any_await("alttpr", hours_past=0.5, hours_future=2)
    assert [c.args for c in create_room.await_args_list] == [("alttpr", 1), ("alttpr", "2")]
    assert published == [events.TournamentRoomCreationFailed(event_slug="alttpr", episode_id=2, error="no players",
                                                             occurred_at=published[0].occurred_at)]
    assert "Encountered a problem when attempting to retrieve SG schedule." in caplog.text


async def test_week_races(monkeypatch, published, schedule):
    monkeypatch.setattr(jobs.tournaments, "TOURNAMENT_DATA", {
        "forms": tournament(submission_form="form.html"),
        "events": tournament(create_scheduled_events=True),
        "needs": tournament(scheduling_needs_channel="chan", scheduling_needs_tracker=True),
        "down": tournament(submission_form="form.html"),
    })
    episode = {"id": 1, "when": "2024-06-01T20:00:00+0000", "channels": [], "match1": {"players": []}}
    schedule.by_event.update(forms=[episode], events=[episode], needs=[episode], down=RuntimeError("down"))
    send_form = mock.AsyncMock()
    monkeypatch.setattr(jobs, "send_race_form", send_form)

    await jobs.week_races()

    send_form.assert_awaited_once_with("forms", episode)
    assert [type(e).__name__ for e in published] == ["TournamentEpisodesRefreshed", "SchedulingNeedsUpdated"]
    assert published[0].episodes == (episode,)
    assert published[1].event_slug == "needs"
    schedule.assert_any_await("forms", hours_past=0, hours_future=168)


async def test_send_race_form(monkeypatch, published):
    race = SimpleNamespace(send_race_submission_form=mock.AsyncMock())
    fetch = mock.AsyncMock(return_value=race)
    monkeypatch.setattr(jobs.tournaments, "fetch_tournament_handler", fetch)

    await jobs.send_race_form("alttpr", {"id": 5})
    fetch.assert_awaited_once_with("alttpr", 5)
    race.send_race_submission_form.assert_awaited_once()
    assert published == []

    race.send_race_submission_form.side_effect = RuntimeError("DMs closed")
    await jobs.send_race_form("alttpr", {"id": "6"})
    [failed] = published
    assert (failed.event_slug, failed.episode_id, failed.error) == ("alttpr", 6, "DMs closed")


async def test_record_races_delegates(monkeypatch):
    record = mock.AsyncMock()
    monkeypatch.setattr(jobs.tournament_results, "record_results", record)
    await jobs.record_races()
    record.assert_awaited_once()


# ---------------------------------------------------------------------------
# Players whose Discord account can't be found
# ---------------------------------------------------------------------------


def player(name, discord_id="", tag="", stream="yes"):
    return {"displayName": name, "discordId": discord_id, "discordTag": tag, "publicStream": stream}


@pytest.fixture
def members(monkeypatch):
    """Guild members known by id and by name."""
    by_id = {11: "alice"}
    by_name = {"bob": "bob"}
    get_member = mock.AsyncMock(side_effect=lambda guild, uid: by_id.get(uid))
    get_named = mock.AsyncMock(side_effect=lambda guild, name: by_name.get(name))
    monkeypatch.setattr(jobs.discord_members, "get_member", get_member)
    monkeypatch.setattr(jobs.discord_members, "get_member_named", get_named)
    return SimpleNamespace(get_member=get_member, get_named=get_named)


async def test_report_bad_player_discord(monkeypatch, schedule, members):
    guild = object()
    monkeypatch.setattr(jobs.tournaments, "TOURNAMENT_DATA", {"alttpr": tournament(guild=guild)})
    schedule.by_event["alttpr"] = [
        {
            "id": 1,
            "match1": {"players": [
                player("Alice", discord_id="11"),
                player("Bob", tag="bob#0"),
                player("Carol", discord_id="33", tag="carol"),
                player("Ignored", stream="ignore"),
                player("Winner of Match 3"),
            ]},
            "match2": None,
        },
        {"id": 2, "match1": {"players": []}, "match2": {"players": [player("Dave", discord_id="not a number")]}},
    ]

    messages = await jobs.report_bad_player_discord("alttpr")

    assert messages == [
        "Episode 1 - alttpr - Carol could not be found",
        "Episode 2 - alttpr - Dave could not be found",
    ]
    members.get_named.assert_any_await(guild, "bob")
    schedule.assert_awaited_with("alttpr", hours_past=0, hours_future=48)


async def test_find_races_with_bad_discord(monkeypatch, published, caplog):
    monkeypatch.setattr(jobs.tournaments, "TOURNAMENT_DATA", {"good": None, "bad": None, "broken": None})

    async def report(slug):
        if slug == "broken":
            raise RuntimeError("no guild")
        return ["Episode 1 - bad - X could not be found"] if slug == "bad" else []

    monkeypatch.setattr(jobs, "report_bad_player_discord", report)

    await jobs.find_races_with_bad_discord()

    [event] = published
    assert (event.event_slug, event.messages) == ("bad", ("Episode 1 - bad - X could not be found",))
    assert "Unable to check player Discord info for broken" in caplog.text
