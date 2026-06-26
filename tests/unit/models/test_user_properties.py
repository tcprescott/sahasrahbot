"""Characterization tests for computed properties on the Users model.

These build in-memory model instances (no DB) and exercise pure property logic.
See alttprbot/models/models.py (Users.racetime_profile).
"""

from alttprbot import models


def test_racetime_profile_none_without_rtgg_id():
    user = models.Users(rtgg_id=None, display_name="someone")
    assert user.racetime_profile is None


def test_racetime_profile_builds_url():
    user = models.Users(rtgg_id="abc123")
    assert user.racetime_profile == f"{models.RACETIME_URL}/user/abc123/"
