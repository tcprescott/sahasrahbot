"""The event bridge (alttprbot/events) and its Discord subscribers."""

import asyncio
import dataclasses
import inspect
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

from alttprbot import events
from alttprbot.events import types as event_types

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _clean_bus():
    events.clear()
    yield
    events.clear()


def run(coro):
    return asyncio.run(coro)


# --- the registry -----------------------------------------------------------

def test_every_event_class_is_registered():
    defined = {
        obj for _, obj in inspect.getmembers(event_types, inspect.isclass)
        if issubclass(obj, events.Event) and obj is not events.Event
    }
    assert defined == set(events.ALL_EVENTS)
    assert set(events.__all__) >= {cls.__name__ for cls in events.ALL_EVENTS}


def test_event_names_are_unique_object_verb():
    names = [cls.name for cls in events.ALL_EVENTS]
    assert len(names) == len(set(names))
    for name in names:
        assert re.fullmatch(r"[a-z_]+\.[a-z_]+", name), name


def test_events_are_frozen():
    event = events.RankedChoiceBallotCast(election_id=1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.election_id = 2
    assert event.occurred_at.tzinfo is not None


def test_events_package_imports_no_front_end():
    """Any layer may publish, so the bridge itself must not pull in a bot or the web app."""
    code = (
        f"import sys; sys.path.insert(0, {str(ROOT)!r}); sys.path.insert(0, {str(ROOT / 'tests')!r})\n"
        "import conftest\n"
        "import alttprbot.events\n"
        "bad = sorted(m for m in sys.modules if m.split('.')[0] in "
        "{'discord', 'alttprbot_discord', 'alttprbot_racetime', 'alttprbot_api', 'alttprbot_audit', 'racetime_bot', 'quart'})\n"
        "assert not bad, bad\n"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr[-4000:]


# --- the bus ----------------------------------------------------------------

def test_publish_delivers_to_matching_subscribers_only():
    received = []

    async def on_ballot(event):
        received.append(("ballot", event.election_id))

    async def on_daily(event):
        received.append(("daily", event.hash_id))

    async def on_anything(event):
        received.append(("any", event.name))

    events.subscribe(events.RankedChoiceBallotCast, on_ballot)
    events.subscribe(events.DailyChallengeAvailable, on_daily)
    events.subscribe(events.Event, on_anything)

    async def main():
        events.publish(events.RankedChoiceBallotCast(election_id=7))
        await events.drain()

    run(main())
    assert sorted(received) == [("any", "ranked_choice.ballot_cast"), ("ballot", 7)]


def test_subscribe_accepts_a_tuple_of_classes_and_unsubscribe_stops_delivery():
    received = []

    async def handler(event):
        received.append(event.name)

    token = events.subscribe((events.RankedChoiceBallotCast, events.DailyChallengeAvailable), handler)

    async def main():
        events.publish(events.DailyChallengeAvailable(hash_id="abc"))
        await events.drain()
        events.unsubscribe(token)
        events.publish(events.DailyChallengeAvailable(hash_id="def"))
        await events.drain()

    run(main())
    assert received == ["daily.challenge_available"]


def test_publish_does_not_wait_for_subscribers():
    order = []

    async def slow(event):
        await asyncio.sleep(0)
        order.append("subscriber")

    events.subscribe(events.RankedChoiceBallotCast, slow)

    async def main():
        events.publish(events.RankedChoiceBallotCast(election_id=1))
        order.append("publisher")
        await events.drain()

    run(main())
    assert order == ["publisher", "subscriber"]


def test_a_failing_subscriber_does_not_reach_the_publisher_or_others(caplog):
    received = []

    async def broken(event):
        raise RuntimeError("boom")

    async def fine(event):
        received.append(event.election_id)

    events.subscribe(events.RankedChoiceBallotCast, broken)
    events.subscribe(events.RankedChoiceBallotCast, fine)

    async def main():
        events.publish(events.RankedChoiceBallotCast(election_id=3))
        await events.drain()

    run(main())
    assert received == [3]
    assert "boom" in caplog.text


def test_publish_without_a_loop_is_dropped_not_raised(caplog):
    async def handler(event):
        raise AssertionError("should not run")

    events.subscribe(events.RankedChoiceBallotCast, handler)
    events.publish(events.RankedChoiceBallotCast(election_id=1))
    assert "no running event loop" in caplog.text


def test_subscribe_rejects_sync_handlers_and_non_events():
    with pytest.raises(TypeError):
        events.subscribe(events.RankedChoiceBallotCast, lambda e: None)

    async def handler(event):
        pass

    with pytest.raises(TypeError):
        events.subscribe(dict, handler)


# --- Discord subscribers ----------------------------------------------------

START = datetime(2026, 11, 23, 20, 0, tzinfo=timezone.utc)
SEED = datetime(2026, 11, 23, 19, 50, tzinfo=timezone.utc)


def room_opened(**overrides):
    fields = dict(
        event_slug="alttprdaily",
        episode_id=123,
        room_name="alttpr/clever-link-1234",
        room_url="https://racetime.gg/alttpr/clever-link-1234",
        title="Daily Race",
        start_time=START,
        seed_time=SEED,
        broadcast_channels=("speedgaming",),
    )
    fields.update(overrides)
    return events.TournamentRoomOpened(**fields)


def test_daily_announcements_match_the_old_wording():
    import discord

    from alttprbot_discord import notifications

    start, start_r = discord.utils.format_dt(START), discord.utils.format_dt(START, "R")
    seed_r = discord.utils.format_dt(SEED, "R")
    url = "https://racetime.gg/alttpr/clever-link-1234"

    assert notifications.daily_announcement(room_opened(), notifications.DAILY_ANNOUNCEMENTS['alttprdaily']) == (
        f"SpeedGaming Daily Race Series - Daily Race - {start} ({start_r}) on speedgaming"
        f" - Seed Distributed {seed_r} - {url}"
    )
    assert notifications.daily_announcement(
        room_opened(event_slug="smz3", broadcast_channels=()), notifications.DAILY_ANNOUNCEMENTS['smz3']
    ) == f"<@&449260882501959700> SMZ3 Weekly Race - Daily Race - {start} ({start_r}) - {url}"


class FakeBot:
    def __init__(self):
        self.channel = mock.AsyncMock()
        self.users = {1: mock.AsyncMock(), 2: mock.AsyncMock()}

    async def wait_until_ready(self):
        pass

    def get_channel(self, channel_id):
        return self.channel

    def get_user(self, user_id):
        return self.users.get(user_id)

    async def fetch_user(self, user_id):
        raise AssertionError("every test user is cached")


def test_room_opened_dms_the_players():
    from alttprbot_discord import notifications

    bot = FakeBot()
    notifications.register(bot)

    async def main():
        events.publish(room_opened(event_slug="alttprleague", versus="a vs. b", player_discord_ids=(1, 2)))
        await events.drain()

    run(main())
    bot.channel.send.assert_not_called()
    for user in bot.users.values():
        embed = user.send.call_args.kwargs['embed']
        assert embed.title == "RT.gg Room Opened - a vs. b"
        assert "https://racetime.gg/alttpr/clever-link-1234" in embed.description


def test_room_opened_dm_failure_does_not_stop_the_others():
    import discord

    from alttprbot_discord import notifications

    bot = FakeBot()
    bot.users[1].send.side_effect = discord.HTTPException(mock.Mock(status=403), "nope")
    notifications.register(bot)

    async def main():
        events.publish(room_opened(event_slug="alttprleague", player_discord_ids=(1, 2)))
        await events.drain()

    run(main())
    bot.users[2].send.assert_awaited_once()


def test_daily_room_opened_posts_the_announcement(monkeypatch):
    import config

    from alttprbot_discord import notifications

    monkeypatch.setattr(config, "SG_DISCORD_WEBHOOK", "")
    bot = FakeBot()
    notifications.register(bot)

    async def main():
        events.publish(room_opened())
        await events.drain()

    run(main())
    content = bot.channel.send.call_args.kwargs['content']
    assert content.startswith("SpeedGaming Daily Race Series - Daily Race")


def test_register_twice_does_not_double_deliver():
    from alttprbot_discord import notifications

    bot = FakeBot()
    notifications.register(bot)
    notifications.register(bot)

    async def main():
        events.publish(room_opened(event_slug="alttprleague", player_discord_ids=(1,)))
        await events.drain()

    run(main())
    assert bot.users[1].send.call_count == 1
