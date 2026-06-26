"""Characterization tests for the pure scoring math in async tournaments.

Targets ``average_timedelta`` and ``calculate_qualifier_score`` from
alttprbot/util/asynctournament.py. Both are pure; no mocking required.
"""

from datetime import timedelta

import pytest

from alttprbot.util.asynctournament import (
    QUALIFIER_MAX_SCORE,
    QUALIFIER_MIN_SCORE,
    average_timedelta,
    calculate_qualifier_score,
)


def td(seconds):
    return timedelta(seconds=seconds)


def test_average_timedelta_multiple():
    assert average_timedelta([td(10), td(20), td(30)]) == td(20)


def test_average_timedelta_single_element():
    assert average_timedelta([td(42)]) == td(42)


def test_average_timedelta_returns_timedelta_type():
    # Guards a refactor that returns raw seconds/float instead of a timedelta.
    assert isinstance(average_timedelta([td(10), td(20)]), timedelta)


def test_average_timedelta_fractional():
    assert average_timedelta([td(10), td(11)]) == td(10.5)


def test_average_timedelta_empty_raises_zero_division():
    """Characterizes current behavior: an empty list divides by zero.

    Production callers always pass a non-empty list, but documenting this
    guards against a regression that would mask the error.
    """
    with pytest.raises(ZeroDivisionError):
        average_timedelta([])


def test_score_equal_to_par_is_100():
    assert calculate_qualifier_score(par_time=td(3600), elapsed_time=td(3600)) == 100


def test_score_slower_than_par_below_100():
    # 1.5x par -> (2 - 1.5) * 100 = 50
    assert calculate_qualifier_score(par_time=td(3600), elapsed_time=td(5400)) == 50


def test_score_in_range_non_boundary_slope():
    # 1.25x par -> (2 - 1.25) * 100 = 75, pins the linear slope away from clamps
    assert calculate_qualifier_score(par_time=td(3600), elapsed_time=td(4500)) == 75


def test_score_twice_as_slow_clamps_to_min():
    # 2x par -> (2 - 2) * 100 = 0
    assert calculate_qualifier_score(par_time=td(3600), elapsed_time=td(7200)) == QUALIFIER_MIN_SCORE


def test_score_much_slower_clamps_to_min_not_negative():
    # 3x par -> (2 - 3) * 100 = -100, clamped to 0
    assert calculate_qualifier_score(par_time=td(3600), elapsed_time=td(10800)) == QUALIFIER_MIN_SCORE


def test_score_faster_than_par_clamps_to_max():
    # half par -> (2 - 0.5) * 100 = 150, clamped to 105
    assert calculate_qualifier_score(par_time=td(3600), elapsed_time=td(1800)) == QUALIFIER_MAX_SCORE


def test_score_just_over_cap_is_clamped():
    # 0.9x par -> (2 - 0.9) * 100 = 110, which the min() clamps down to 105.
    # Inputs chosen so the raw value EXCEEDS the cap (unlike a value sitting
    # exactly on it), so this independently proves the upper clamp.
    assert calculate_qualifier_score(par_time=td(2000), elapsed_time=td(1800)) == QUALIFIER_MAX_SCORE
