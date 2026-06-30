"""Characterization tests for AsyncTournamentRace computed properties.

Most properties are pure functions of scalar fields and are exercised against
in-memory instances. ``url`` touches the ``live_race``/``tournament`` relations,
so that test assigns in-memory related objects (under the tortoise_db fixture so
the ORM is initialized).

See alttprbot/models/models.py.
"""

from datetime import datetime, timedelta, timezone

import discord
import pytest

from alttprbot import models


def make_race(**kwargs):
    return models.AsyncTournamentRace(**kwargs)


UTC = timezone.utc


# ---- elapsed_time -------------------------------------------------------

def test_elapsed_time_none_without_start():
    assert make_race(status="finished").elapsed_time is None


def test_elapsed_time_finished_is_end_minus_start():
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = start + timedelta(hours=1, minutes=1, seconds=1)
    race = make_race(status="finished", start_time=start, end_time=end)
    assert race.elapsed_time == timedelta(hours=1, minutes=1, seconds=1)


def test_elapsed_time_pending_is_none_even_with_start():
    race = make_race(status="pending", start_time=datetime(2024, 1, 1, tzinfo=UTC))
    assert race.elapsed_time is None


def test_elapsed_time_in_progress_is_positive():
    start = discord.utils.utcnow() - timedelta(minutes=10)
    race = make_race(status="in_progress", start_time=start)
    assert race.elapsed_time is not None
    assert race.elapsed_time > timedelta(minutes=9)


# ---- elapsed_time_formatted --------------------------------------------

def test_elapsed_time_formatted_na_when_none():
    assert make_race(status="pending").elapsed_time_formatted == "N/A"


def test_elapsed_time_formatted_value():
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = start + timedelta(seconds=3661)
    assert make_race(status="finished", start_time=start, end_time=end).elapsed_time_formatted == "01:01:01"


# ---- status_formatted ---------------------------------------------------

@pytest.mark.parametrize(
    "status, expected",
    [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("finished", "Finished"),
        ("forfeit", "Forfeit"),
        ("disqualified", "Disqualified"),
        ("something_else", "Unknown"),
    ],
)
def test_status_formatted(status, expected):
    assert make_race(status=status).status_formatted == expected


# ---- score_formatted ----------------------------------------------------

def test_score_formatted_value():
    assert make_race(status="finished", score=99.123456).score_formatted == "99.123"


def test_score_formatted_rounds_to_three_places():
    # 88.8888 -> "88.889": pins that :.3f rounds (not truncates) the 4th decimal.
    assert make_race(status="finished", score=88.8888).score_formatted == "88.889"


def test_score_formatted_pending_na():
    assert make_race(status="pending", score=None).score_formatted == "N/A"


def test_score_formatted_finished_not_calculated():
    assert make_race(status="finished", score=None).score_formatted == "not calculated"


# ---- is_closed ----------------------------------------------------------

@pytest.mark.parametrize(
    "status, expected",
    [("finished", True), ("forfeit", True), ("disqualified", True), ("pending", False), ("in_progress", False)],
)
def test_is_closed(status, expected):
    assert make_race(status=status).is_closed() is expected


# ---- review_status_formatted -------------------------------------------

@pytest.mark.parametrize(
    "review_status, expected",
    [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        # Note the surprising mapping: 'rejected' -> 'Pending Second Review'.
        ("rejected", "Pending Second Review"),
        ("weird", "Unknown"),
    ],
)
def test_review_status_formatted_mapping(review_status, expected):
    race = make_race(status="finished", reattempted=False, review_status=review_status)
    race.live_race = None
    assert race.review_status_formatted == expected


def test_review_status_formatted_na_when_reattempted():
    race = make_race(status="finished", reattempted=True, review_status="pending")
    race.live_race = None
    assert race.review_status_formatted == "N/A"


def test_review_status_formatted_na_when_not_finished():
    race = make_race(status="in_progress", reattempted=False, review_status="pending")
    race.live_race = None
    assert race.review_status_formatted == "N/A"


# ---- runner_notes_html --------------------------------------------------

def test_runner_notes_html_none_when_unset():
    assert make_race(runner_notes=None).runner_notes_html is None


def test_runner_notes_html_renders_markdown():
    result = make_race(runner_notes="**bold**").runner_notes_html
    assert "<strong>bold</strong>" in result


def test_runner_notes_html_converts_newlines():
    result = make_race(runner_notes="line1\nline2").runner_notes_html
    assert "<br/>" in result


# ---- url (relations) ----------------------------------------------------

def test_url_uses_thread_when_no_live_race(tortoise_db):
    race = make_race(thread_id=555, status="pending")
    race.tournament = models.AsyncTournament(guild_id=42, name="t", channel_id=1, owner_id=1)
    race.live_race = None
    assert race.url == "https://discord.com/channels/42/555"


def test_url_none_when_no_thread_and_no_live_race(tortoise_db):
    race = make_race(thread_id=None, status="pending")
    race.live_race = None
    assert race.url is None


def test_url_uses_live_race_racetime_url(tortoise_db):
    race = make_race(status="finished")
    race.live_race = models.AsyncTournamentLiveRace(racetime_slug="alttpr/abc")
    assert race.url == f"{models.RACETIME_URL}/alttpr/abc"


def test_url_none_when_live_race_has_no_slug(tortoise_db):
    # A truthy live_race short-circuits the thread_url fallback even when its
    # racetime_url is None, so url is None despite thread_id being set.
    race = make_race(status="finished", thread_id=777)
    race.live_race = models.AsyncTournamentLiveRace(racetime_slug=None)
    assert race.url is None
