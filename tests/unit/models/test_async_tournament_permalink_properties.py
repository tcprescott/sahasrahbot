"""Characterization tests for AsyncTournamentPermalink computed properties.

See alttprbot/models/models.py (par_time_timedelta / par_time_formatted).
"""

from datetime import timedelta

import pytest

from alttprbot import models


def make_permalink(par_time):
    return models.AsyncTournamentPermalink(par_time=par_time, url="https://alttpr.com/h/X")


def test_par_time_timedelta_none_when_unset():
    assert make_permalink(None).par_time_timedelta is None


def test_par_time_timedelta_from_seconds():
    assert make_permalink(3661.0).par_time_timedelta == timedelta(seconds=3661)


def test_par_time_formatted():
    assert make_permalink(3661.0).par_time_formatted == "01:01:01"


def test_par_time_formatted_truncates_fractional_seconds():
    # .seconds drops the fractional part, so 3661.9 still formats as 01:01:01.
    assert make_permalink(3661.9).par_time_formatted == "01:01:01"


def test_par_time_formatted_drops_days_over_24h():
    """Characterizes a quirk: par_time_formatted uses timedelta.seconds (not
    total_seconds), which discards whole days. 90061s (~25h) formats as the
    leftover 01:01:01, not 25:01:01."""
    assert make_permalink(90061.0).par_time_formatted == "01:01:01"


def test_par_time_formatted_raises_when_unset():
    """Characterizes current behavior: formatting a None par_time raises.

    par_time_formatted dereferences par_time_timedelta (which is None) without
    a guard, so callers must check par_time before formatting.
    """
    with pytest.raises(AttributeError):
        _ = make_permalink(None).par_time_formatted
