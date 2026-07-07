"""Regression test: KONOT.resume must raise for a non-KONOT room.

SahasrahBotCoreHandler.setup_konot() catches KONOTSegmentNotFound as the normal
"this room is not a KONOT race" path (a SahasrahBotException, replacing the old
tortoise DoesNotExist so presentation no longer imports the ORM library).
"""

import pytest

from alttprbot.exceptions import KONOTSegmentNotFound, SahasrahBotException
from alttprbot.presentation.racetime.misc.konot import KONOT


class _FakeHandler:
    def __init__(self, name):
        self.data = {"name": name}


async def test_resume_raises_segment_not_found_for_unknown_room(tortoise_db):
    with pytest.raises(KONOTSegmentNotFound):
        await KONOT.resume(_FakeHandler("category/no-such-room"))


def test_konot_segment_not_found_is_domain_exception():
    assert issubclass(KONOTSegmentNotFound, SahasrahBotException)
