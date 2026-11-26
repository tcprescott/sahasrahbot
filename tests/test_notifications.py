"""Discord output of the scheduled jobs and the racetime/ranked-choice subscribers
(alttprbot_discord/notifications.py).

``tests/test_events.py`` covers delivery through the bus and the tournament engine
posts; this file calls the remaining handlers directly with fake Discord objects.
"""

import datetime
from types import SimpleNamespace
from unittest import mock

import discord
import pytest

from alttprbot import events, models
from alttprbot.services import guild_config
from alttprbot_discord import notifications
from tests.discord_fakes import FakeChannel, FakeGuild, FakeMessage

NOW = datetime.datetime(2024, 6, 1, 18, 0, tzinfo=datetime.timezone.utc)


class Bot:
    def __init__(self, channels=(), guilds=(), ready=True):
        self.channels = {c.id: c for c in channels}
        self.guilds = {g.id: g for g in guilds}
        self.ready = ready
        self.user = SimpleNamespace(id=999)
        self.emojis = []

    def is_ready(self):
        return self.ready

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_guild(self, guild_id):
        return self.guilds.get(guild_id)


async def test_wait_until_ready_polls(monkeypatch):
    bot = Bot(ready=False)
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)
        bot.ready = len(sleeps) == 2

    monkeypatch.setattr(notifications.asyncio, "sleep", fake_sleep)
    await notifications.wait_until_ready(bot)
    assert sleeps == [1, 1]


# ---------------------------------------------------------------------------
# Scheduling needs
# ---------------------------------------------------------------------------


def need(hours, count):
    return events.StaffNeed(start_time=NOW + datetime.timedelta(hours=hours), count=count,
                            signup_url=f"https://sg.test/{hours}")


@pytest.mark.parametrize("include_trackers", [True, False])
def test_scheduling_needs_embed(include_trackers):
    event = events.SchedulingNeedsUpdated(event_slug="alttpr", commentators=(need(1, 2),),
                                          broadcasters=(need(3, 1),))
    embed = notifications.build_scheduling_needs_embed(event, include_trackers=include_trackers)

    names = [f.name for f in embed.fields]
    assert names == (["Commentators Needed", "Trackers Needed", "Broadcasters Needed"] if include_trackers
                     else ["Commentators Needed", "Broadcasters Needed"])
    stamp = discord.utils.format_dt(NOW + datetime.timedelta(hours=1), "f")
    assert embed.fields[0].value == f"*{stamp}* - Need **2** - [Sign Up!](https://sg.test/1)"
    if include_trackers:
        assert embed.fields[1].value == "No current needs."


def test_scheduling_needs_embed_without_broadcasters():
    embed = notifications.build_scheduling_needs_embed(events.SchedulingNeedsUpdated(event_slug="x"), False)
    assert [(f.name, f.value) for f in embed.fields] == [("Commentators Needed", "No current needs.")]


class History:
    """``channel.history()``: an async iterator over the given messages."""

    def __init__(self, messages):
        self.messages = messages

    def __call__(self, limit):
        async def gen():
            for m in self.messages:
                yield m
        return gen()


def job_output(monkeypatch, bot, **config):
    """A ScheduledJobDiscordOutput whose event config is a SimpleNamespace."""
    jobs = notifications.ScheduledJobDiscordOutput(bot)
    event_config = SimpleNamespace(
        audit_channel=config.get("audit_channel"),
        guild=config.get("guild"),
        data=SimpleNamespace(scheduling_needs_channel=config.get("needs_channel"),
                             scheduling_needs_tracker=config.get("trackers", False)),
    )
    jobs._event_config = mock.AsyncMock(return_value=event_config)
    return jobs


async def test_scheduling_needs_edits_the_bots_last_post(monkeypatch):
    bot = Bot()
    ours, theirs = FakeMessage(author=bot.user), FakeMessage(author="someone")
    channel = FakeChannel()
    channel.history = History([theirs, ours])
    jobs = job_output(monkeypatch, bot, needs_channel=channel)

    await jobs.update_scheduling_needs(events.SchedulingNeedsUpdated(event_slug="alttpr"))

    ours.edit.assert_awaited_once()
    theirs.edit.assert_not_awaited()
    channel.send.assert_not_awaited()


async def test_scheduling_needs_posts_when_nothing_to_edit(monkeypatch):
    channel = FakeChannel()
    channel.history = History([FakeMessage(author="someone")])
    jobs = job_output(monkeypatch, Bot(), needs_channel=channel, trackers=True)

    await jobs.update_scheduling_needs(events.SchedulingNeedsUpdated(event_slug="alttpr"))

    embed = channel.send.await_args.kwargs["embed"]
    assert "Trackers Needed" in [f.name for f in embed.fields]


async def test_scheduling_needs_without_channel_or_on_error(monkeypatch, caplog):
    jobs = job_output(monkeypatch, Bot())
    await jobs.update_scheduling_needs(events.SchedulingNeedsUpdated(event_slug="alttpr"))  # no channel: nothing

    channel = FakeChannel()
    channel.history = mock.Mock(side_effect=discord.Forbidden(mock.Mock(status=403), "no"))
    jobs = job_output(monkeypatch, Bot(), needs_channel=channel)
    await jobs.update_scheduling_needs(events.SchedulingNeedsUpdated(event_slug="alttpr"))
    assert "Unable to update scheduling needs channel." in caplog.text


# ---------------------------------------------------------------------------
# Audit-channel reports
# ---------------------------------------------------------------------------


async def test_job_failure_reports(monkeypatch):
    audit = FakeChannel()
    jobs = job_output(monkeypatch, Bot(), audit_channel=audit)

    await jobs.report_room_creation_failed(events.TournamentRoomCreationFailed(event_slug="alttpr", episode_id=5,
                                                                               error="boom"))
    await jobs.report_submission_reminder_failed(events.RaceSubmissionReminderFailed(event_slug="alttpr",
                                                                                     episode_id=6, error="bang"))
    await jobs.report_unmatched_players(events.UnmatchedPlayersFound(event_slug="alttpr", messages=("a", "b")))

    texts = [m.content for m in audit.sent]
    assert texts[0] == "There was an error while automatically creating a race room for episode `5`.\n\nboom"
    assert texts[1] == "There was an error while sending a submission reminder for episode `6`.\n\nbang"
    assert texts[2] == f"{notifications.BAD_DISCORD_REPORT_MENTION}\n\na\nb"
    assert audit.sent[0].allowed_mentions.everyone is True


async def test_job_failure_reports_without_audit_channel(monkeypatch):
    jobs = job_output(monkeypatch, Bot())
    await jobs.report_room_creation_failed(events.TournamentRoomCreationFailed(event_slug="x", episode_id=1, error="e"))
    await jobs.report_submission_reminder_failed(events.RaceSubmissionReminderFailed(event_slug="x", episode_id=1,
                                                                                     error="e"))
    await jobs.report_unmatched_players(events.UnmatchedPlayersFound(event_slug="x"))


async def test_event_config_looks_up_the_tournament(monkeypatch):
    config = object()
    handler = SimpleNamespace(get_config=mock.AsyncMock(return_value=config))
    monkeypatch.setattr(notifications.tournaments, "TOURNAMENT_DATA", {"alttpr": handler})
    jobs = notifications.ScheduledJobDiscordOutput(Bot())
    assert await jobs._event_config("alttpr") is config


# ---------------------------------------------------------------------------
# Daily challenge announcement
# ---------------------------------------------------------------------------


async def test_announce_daily_posts_in_configured_channels(db, monkeypatch, caplog):
    from alttprbot_discord.cogs import daily

    seed = SimpleNamespace(data={"spoiler": {"meta": {"name": "Daily Challenge: Hard"}}})
    monkeypatch.setattr(daily, "get_daily_seed", mock.AsyncMock(return_value=seed))
    monkeypatch.setattr(notifications, "seed_embed", mock.AsyncMock(return_value=discord.Embed(title="daily")))
    posted = FakeMessage()
    posted.create_thread = mock.AsyncMock()
    good = FakeChannel(channel_id=1, name="daily")
    good.send = mock.AsyncMock(return_value=posted)
    broken = FakeChannel(channel_id=2, name="broken")
    broken.send = mock.AsyncMock(side_effect=discord.Forbidden(mock.Mock(status=403), "no"))
    guild = FakeGuild(guild_id=10, channels=[good, broken])
    guild.text_channels = guild.channels
    await guild_config.set_value(10, "DailyAnnouncerChannel", "daily,missing,broken")
    await guild_config.set_value(11, "DailyAnnouncerChannel", "daily")  # a guild the bot left
    jobs = notifications.ScheduledJobDiscordOutput(Bot(guilds=[guild]))

    await jobs.announce_daily(events.DailyChallengeAvailable(hash_id="abc"))

    assert good.send.await_args.kwargs["embed"].title == "daily"
    posted.create_thread.assert_awaited_once_with(name="Daily Challenge: Hard", auto_archive_duration=1440)
    assert notifications.seed_embed.await_args.kwargs["notes"] == notifications.DAILY_NOTES
    # The channels grant the bot nothing, so no external emojis are offered (#52).
    assert notifications.seed_embed.await_args.kwargs["emojis"] == []
    assert "Daily announcer guild 11 is not available." in caplog.text
    assert "Daily announcer channel missing not found in guild 10." in caplog.text
    assert "Unable to announce the daily in 10/broken." in caplog.text


# ---------------------------------------------------------------------------
# Guild scheduled events mirroring SpeedGaming episodes
# ---------------------------------------------------------------------------


def episode(episode_id, when="2024-06-01T20:00:00+0000"):
    return {"id": episode_id, "when": when}


def race(friendly_name="Week 1", versus="A vs. B", broadcast=(), twitch=()):
    return SimpleNamespace(event_slug="alttpr", friendly_name=friendly_name, versus=versus,
                           broadcast_channels=list(broadcast), player_twitch_names=list(twitch))


@pytest.mark.parametrize(
    "tournament_race, name, location",
    [
        (race(broadcast=("speedgaming",)), "ALTTPR - Week 1 - A vs. B", "https://twitch.tv/speedgaming"),
        (race(friendly_name=None, twitch=("a", "b")), "ALTTPR - A vs. B", "https://multistre.am/a/b/layout3/"),
        (race(friendly_name=None, versus=None), "ALTTPR", "TBD"),
    ],
)
def test_scheduled_event_details(tournament_race, name, location):
    details = notifications._scheduled_event_details(tournament_race, episode(1))
    start = datetime.datetime(2024, 6, 1, 20, tzinfo=datetime.timezone.utc)
    assert details == {
        "name": name,
        "description": f"Start Time: {discord.utils.format_dt(start, 'f')}",
        "start_time": start,
        "end_time": start + datetime.timedelta(hours=2),
        "location": location,
    }


def test_scheduled_event_name_is_capped_at_100():
    details = notifications._scheduled_event_details(race(versus="x" * 200), episode(1))
    assert len(details["name"]) == 100


class GuildEvents:
    """A guild with scheduled events, keyed by id."""

    def __init__(self, existing=()):
        self.events = {e.id: e for e in existing}
        self.next_id = 5000
        self.created = []

    async def create_scheduled_event(self, **kwargs):
        self.next_id += 1
        event = SimpleNamespace(id=self.next_id, status=discord.EventStatus.scheduled, edit=mock.AsyncMock(),
                                delete=mock.AsyncMock(), **{k: kwargs[k] for k in
                                                            ("name", "description", "start_time", "end_time",
                                                             "location")})
        self.created.append(kwargs)
        self.events[event.id] = event
        return event

    async def fetch_scheduled_event(self, event_id):
        if event_id not in self.events:
            raise discord.NotFound(mock.Mock(status=404), "Unknown event")
        return self.events[event_id]


async def test_update_scheduled_events_syncs_guild_events(db, monkeypatch):
    stale = SimpleNamespace(id=1, status=discord.EventStatus.scheduled, delete=mock.AsyncMock())
    finished = SimpleNamespace(id=2, status=discord.EventStatus.completed, delete=mock.AsyncMock())
    outdated = SimpleNamespace(id=3, status=discord.EventStatus.scheduled, edit=mock.AsyncMock(),
                               name="old", description="", start_time=None, end_time=None, location="")
    guild = GuildEvents([stale, finished, outdated])
    await models.ScheduledEvents.create(scheduled_event_id=1, episode_id=101, event_slug="alttpr")
    await models.ScheduledEvents.create(scheduled_event_id=2, episode_id=102, event_slug="alttpr")
    await models.ScheduledEvents.create(scheduled_event_id=3, episode_id=103, event_slug="alttpr")
    await models.ScheduledEvents.create(scheduled_event_id=9, episode_id=109, event_slug="other")  # other event

    async def handler(slug, ep):
        if ep["id"] == 107:
            raise RuntimeError("bad episode")
        return race(broadcast=("speedgaming",))

    monkeypatch.setattr(notifications.tournaments, "fetch_tournament_handler_v2", handler)
    jobs = job_output(monkeypatch, Bot(), guild=guild)

    await jobs.update_scheduled_events(events.TournamentEpisodesRefreshed(
        event_slug="alttpr", episodes=(episode(103), episode(105), episode(107)),
    ))

    stale.delete.assert_awaited_once()
    finished.delete.assert_not_awaited()  # completed events stay in Discord
    outdated.edit.assert_awaited_once()
    assert outdated.edit.await_args.kwargs["entity_type"] == discord.EntityType.external
    rows = {r.episode_id: (r.scheduled_event_id, r.event_slug) for r in await models.ScheduledEvents.all()}
    assert rows == {103: (3, "alttpr"), 105: (5001, "alttpr"), 109: (9, "other")}
    assert [c["name"] for c in guild.created] == ["ALTTPR - Week 1 - A vs. B"]


async def test_known_issue_dead_episode_row_kept_when_guild_event_is_gone(db, monkeypatch):
    """KNOWN ISSUE, pinned not endorsed: when SpeedGaming drops an episode whose guild
    event was already deleted in Discord, the NotFound ``continue``s past the row
    delete, so the stale ScheduledEvents row stays and is retried every refresh."""
    await models.ScheduledEvents.create(scheduled_event_id=4, episode_id=104, event_slug="alttpr")
    jobs = job_output(monkeypatch, Bot(), guild=GuildEvents())

    await jobs.update_scheduled_events(events.TournamentEpisodesRefreshed(event_slug="alttpr", episodes=()))

    assert await models.ScheduledEvents.exists(episode_id=104)


async def test_recreated_guild_event_is_recorded(db, monkeypatch):
    """When a guild event was deleted by hand, a new one is made and its id replaces
    the dead one, so the next refresh finds it instead of making another."""
    await models.ScheduledEvents.create(scheduled_event_id=6, episode_id=106, event_slug="alttpr")
    monkeypatch.setattr(notifications.tournaments, "fetch_tournament_handler_v2", mock.AsyncMock(return_value=race()))
    guild = GuildEvents()
    jobs = job_output(monkeypatch, Bot(), guild=guild)
    refresh = events.TournamentEpisodesRefreshed(event_slug="alttpr", episodes=(episode(106),))

    await jobs.update_scheduled_events(refresh)
    await jobs.update_scheduled_events(refresh)

    assert len(guild.created) == 1
    [row] = await models.ScheduledEvents.filter(episode_id=106)
    assert row.scheduled_event_id != 6


async def test_sync_leaves_an_up_to_date_event_alone(db):
    details = notifications._scheduled_event_details(race(), episode(1))
    current = SimpleNamespace(id=3, edit=mock.AsyncMock(), **details)
    guild = GuildEvents([current])
    row = await models.ScheduledEvents.create(scheduled_event_id=3, episode_id=1, event_slug="alttpr")

    await notifications._sync_scheduled_event(guild, "alttpr", 1, row, details)

    current.edit.assert_not_awaited()


async def test_update_scheduled_events_logs_sync_errors(db, monkeypatch, caplog):
    guild = mock.Mock(create_scheduled_event=mock.AsyncMock(side_effect=discord.HTTPException(mock.Mock(status=400),
                                                                                              "bad")))
    monkeypatch.setattr(notifications.tournaments, "fetch_tournament_handler_v2", mock.AsyncMock(return_value=race()))
    jobs = job_output(monkeypatch, Bot(), guild=guild)
    await jobs.update_scheduled_events(events.TournamentEpisodesRefreshed(event_slug="alttpr", episodes=(episode(1),)))
    assert "Unable to create guild event." in caplog.text


# ---------------------------------------------------------------------------
# racetime.gg watchers
# ---------------------------------------------------------------------------


def status(new_status="in_progress", entrants=("rt1", "rt2")):
    return events.RaceStatusChanged(category="alttpr", room_name="clever-link-1234",
                                    room_url="https://racetime.test/alttpr/clever-link-1234",
                                    base_url="https://racetime.test", status=new_status, entrant_ids=entrants)


@pytest.fixture
def racetime_users(monkeypatch):
    users = {
        "rt1": {"url": "/user/rt1", "full_name": "Veteran#1", "stats": {"joined": 50}},
        "rt2": {"url": "/user/rt2", "full_name": "Newbie#2", "stats": {"joined": 0}},
    }
    get = mock.AsyncMock(side_effect=lambda rid, base_url: users[rid])
    monkeypatch.setattr(notifications.racetime, "get_user", get)
    return get


async def test_race_start_reports_watchlisted_and_new_players(db, racetime_users):
    watch_channel, new_channel = FakeChannel(channel_id=1), FakeChannel(channel_id=2)
    watcher = await models.RTGGWatcher.create(guild_id=1, channel_id=1, category="alttpr")
    await models.RTGGWatcherPlayer.create(rtgg_watcher=watcher, racetime_id="rt1")
    await models.RTGGWatcher.create(guild_id=1, channel_id=2, category="alttpr", notify_on_new_player=True)
    await models.RTGGWatcher.create(guild_id=1, channel_id=3, category="smz3", notify_on_new_player=True)
    notifier = notifications.DiscordNotifier(Bot(channels=[watch_channel, new_channel]))

    await notifier.on_race_status_changed(status())

    [watched] = watch_channel.sent
    assert watched.embed.title == "Watchlisted Player Detected in race"
    assert "[Veteran#1](https://racetime.test/user/rt1)" in watched.embed.description
    [new] = new_channel.sent
    assert new.embed.title == "New Racer Detected!"
    assert "[Newbie#2](https://racetime.test/user/rt2) began racing in [clever-link-1234]" in new.embed.description
    racetime_users.assert_any_await("rt1", base_url="https://racetime.test")


async def test_race_status_other_than_start_is_ignored(db, racetime_users):
    notifier = notifications.DiscordNotifier(Bot())
    await notifier.on_race_status_changed(status("finished"))
    await notifier.on_race_status_changed(status(entrants=()))
    racetime_users.assert_not_awaited()


# ---------------------------------------------------------------------------
# Elections
# ---------------------------------------------------------------------------


async def test_election_events_refresh_or_delete_the_post(monkeypatch):
    refresh = mock.AsyncMock()
    delete_post = mock.AsyncMock()
    monkeypatch.setattr(notifications.election_posts, "refresh", refresh)
    monkeypatch.setattr(notifications.election_posts, "delete_post", delete_post)
    bot = Bot()
    notifier = notifications.DiscordNotifier(bot)

    for event in (events.ElectionBallotCast(election_id=4), events.ElectionUpdated(election_id=4),
                  events.ElectionClosed(election_id=4)):
        await notifier.on_election_changed(event)
    await notifier.on_election_deleted(events.ElectionDeleted(election_id=4, channel_id=300, message_id=700))

    assert [c.args for c in refresh.await_args_list] == [(bot, 4)] * 3
    delete_post.assert_awaited_once_with(bot, 300, 700)


# ---------------------------------------------------------------------------
# SpeedGaming daily webhook
# ---------------------------------------------------------------------------


async def test_daily_announcement_also_goes_to_the_sg_webhook(monkeypatch):
    sent = []

    class FakeWebhook:
        @classmethod
        def from_url(cls, url, session):
            sent.append(("url", url))
            return cls()

        async def send(self, content, username):
            sent.append((content, username))

    monkeypatch.setattr(notifications.config, "SG_DISCORD_WEBHOOK", "https://discord.test/api/webhooks/1/x")
    monkeypatch.setattr(notifications.discord, "Webhook", FakeWebhook)
    settings = {"channel_id": 1, "heading": "Daily", "mention": None, "webhook_mention": "<@&5>",
                "show_seed_time": False}
    event = events.TournamentRoomOpened(event_slug="x", episode_id=1, room_url="https://racetime.test/r",
                                        room_name="r",
                                        title="Race", start_time=NOW, versus="", broadcast_channels=())
    notifier = notifications.DiscordNotifier(Bot())  # the channel isn't found: logged, webhook still sent

    await notifier._announce_daily(event, settings)

    assert sent[0] == ("url", "https://discord.test/api/webhooks/1/x")
    content, username = sent[1]
    assert content.startswith("<@&5> Daily - Race - ") and username == "SahasrahBot"
