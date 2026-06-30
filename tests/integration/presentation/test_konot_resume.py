"""Regression test: KONOT.resume must raise DoesNotExist for a non-KONOT room.

SahasrahBotCoreHandler.setup_konot() catches tortoise.exceptions.DoesNotExist as the
normal "this room is not a KONOT race" path; the three-tier migration must preserve it.
"""

import pytest
from tortoise.exceptions import DoesNotExist

from alttprbot.presentation.racetime.misc.konot import KONOT


class _FakeHandler:
    def __init__(self, name):
        self.data = {"name": name}


async def test_resume_raises_does_not_exist_for_unknown_room(tortoise_db):
    with pytest.raises(DoesNotExist):
        await KONOT.resume(_FakeHandler("category/no-such-room"))
