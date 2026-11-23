"""Characterization tests for computed properties on the Tortoise models."""

from datetime import datetime, timedelta, timezone

import pytest

import config
from alttprbot import models

T0 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)


def race(**kwargs):
    kwargs.setdefault("status", "finished")
    kwargs.setdefault("live_race", None)
    return models.AsyncTournamentRace(**kwargs)


def test_users_racetime_profile(db):
    assert models.Users(rtgg_id=None).racetime_profile is None
    assert models.Users(rtgg_id="abc").racetime_profile == f"{config.RACETIME_URL}/user/abc/"


def test_permalink_par_time(db):
    assert models.AsyncTournamentPermalink(par_time=None).par_time_timedelta is None
    pl = models.AsyncTournamentPermalink(par_time=3723.9)
    assert pl.par_time_timedelta == timedelta(seconds=3723.9)
    assert pl.par_time_formatted == "01:02:03"


def test_live_race_racetime_url(db):
    assert models.AsyncTournamentLiveRace(racetime_slug=None).racetime_url is None
    assert (
        models.AsyncTournamentLiveRace(racetime_slug="alttpr/cool-race-1234").racetime_url
        == f"{config.RACETIME_URL}/alttpr/cool-race-1234"
    )


class TestAsyncTournamentRace:
    def test_elapsed_time_finished(self, db):
        r = race(start_time=T0, end_time=T0 + timedelta(hours=1, minutes=2, seconds=3))
        assert r.elapsed_time == timedelta(hours=1, minutes=2, seconds=3)
        assert r.elapsed_time_formatted == "01:02:03"

    def test_elapsed_time_not_started(self, db):
        r = race(start_time=None)
        assert r.elapsed_time is None
        assert r.elapsed_time_formatted == "N/A"

    @pytest.mark.parametrize("status", ["pending", "forfeit", "disqualified"])
    def test_elapsed_time_none_unless_finished_or_running(self, db, status):
        assert race(status=status, start_time=T0, end_time=T0 + timedelta(hours=1)).elapsed_time is None

    def test_elapsed_time_in_progress_counts_from_start(self, db):
        r = race(status="in_progress", start_time=datetime.now(timezone.utc) - timedelta(minutes=5))
        assert timedelta(minutes=5) <= r.elapsed_time < timedelta(minutes=6)

    def test_known_issue_elapsed_time_formatted_drops_whole_days(self, db):
        """KNOWN ISSUE, pinned not endorsed: uses ``timedelta.seconds``, so a
        run over 24 hours shows only the remainder (25h -> "01:00:00")."""
        r = race(start_time=T0, end_time=T0 + timedelta(hours=25))
        assert r.elapsed_time_formatted == "01:00:00"

    @pytest.mark.parametrize(
        "status, expected",
        [
            ("pending", "Pending"),
            ("in_progress", "In Progress"),
            ("finished", "Finished"),
            ("forfeit", "Forfeit"),
            ("disqualified", "Disqualified"),
            ("bogus", "Unknown"),
        ],
    )
    def test_status_formatted(self, db, status, expected):
        assert race(status=status).status_formatted == expected

    @pytest.mark.parametrize(
        "review_status, expected",
        [
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("rejected", "Pending Second Review"),
            # KNOWN ISSUE: the scorer's only_approved filter uses "approved",
            # which the display (and the review form) don't know about.
            ("approved", "Unknown"),
        ],
    )
    def test_review_status_formatted(self, db, review_status, expected):
        assert race(review_status=review_status).review_status_formatted == expected

    def test_review_status_formatted_na_cases(self, db):
        assert race(review_status="accepted", reattempted=True).review_status_formatted == "N/A"
        assert race(review_status="accepted", status="forfeit").review_status_formatted == "N/A"

    @pytest.mark.parametrize(
        "status, score, expected",
        [
            ("pending", None, "N/A"),
            ("in_progress", None, "N/A"),
            ("finished", None, "not calculated"),
            ("forfeit", None, "not calculated"),
            ("finished", 98.76543, "98.765"),
            ("forfeit", 0, "0.000"),
        ],
    )
    def test_score_formatted(self, db, status, score, expected):
        assert race(status=status, score=score).score_formatted == expected

    def test_times_formatted_in_us_eastern(self, db):
        r = race(thread_open_time=T0, reviewed_at=T0)
        assert r.thread_open_time_formatted == "2024-01-01 07:00:00"
        assert r.reviewed_at_formatted == "2024-01-01 07:00:00"
        empty = race(thread_open_time=None, reviewed_at=None)
        assert empty.thread_open_time_formatted == "N/A"
        assert empty.reviewed_at_formatted == ""

    @pytest.mark.parametrize(
        "status, closed",
        [("finished", True), ("forfeit", True), ("disqualified", True), ("pending", False), ("in_progress", False)],
    )
    def test_is_closed(self, db, status, closed):
        assert race(status=status).is_closed() is closed

    def test_runner_notes_html_strips_tags_and_renders_markdown(self, db):
        assert race(runner_notes=None).runner_notes_html is None
        html = race(runner_notes="<script>x</script>**bold**\nline2").runner_notes_html
        assert "<script>" not in html
        assert "<strong>bold</strong>" in html
        assert "<br/>" in html

    async def test_thread_url_and_url(self, db):
        tournament = await models.AsyncTournament.create(name="t", guild_id=111, channel_id=222, owner_id=1)
        r = race(thread_id=333)
        r.tournament = tournament
        assert r.thread_url == "https://discord.com/channels/111/333"
        assert r.url == r.thread_url
        assert race(thread_id=None).thread_url is None

        live = models.AsyncTournamentLiveRace(racetime_slug="alttpr/x")
        r_live = race(thread_id=333)
        r_live.live_race = live
        assert r_live.url == f"{config.RACETIME_URL}/alttpr/x"
        assert r_live.review_status_formatted == "N/A"
