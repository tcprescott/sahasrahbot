"""Characterization tests for alttprbot/util/helpers.py."""

import string

from alttprbot.util.helpers import generate_random_string

ALLOWED = set(string.ascii_letters + string.digits)


def test_length_matches_request():
    assert len(generate_random_string(16)) == 16


def test_zero_length_is_empty():
    assert generate_random_string(0) == ""


def test_single_char():
    result = generate_random_string(1)
    assert len(result) == 1
    assert result in ALLOWED


def test_only_uses_alphanumeric_charset():
    result = generate_random_string(200)
    assert set(result) <= ALLOWED


def test_successive_calls_differ():
    # With a 62-char alphabet and length 32 a collision is astronomically
    # unlikely; this guards against an accidental constant/empty return.
    assert generate_random_string(32) != generate_random_string(32)
