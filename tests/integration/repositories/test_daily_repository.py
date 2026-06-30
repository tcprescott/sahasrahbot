"""DailyRepository round-trip tests against an in-memory SQLite database.

See alttprbot/repositories/daily_repository.py.
"""

from alttprbot import models
from alttprbot.repositories import DailyRepository


async def test_exists_by_hash_reflects_create(tortoise_db):
    assert await DailyRepository.exists_by_hash("ABCDE") is False

    created = await DailyRepository.create("ABCDE")

    assert created.hash == "ABCDE"
    assert await DailyRepository.exists_by_hash("ABCDE") is True
    # a different hash is still absent
    assert await DailyRepository.exists_by_hash("ZZZZZ") is False


async def test_create_persists_row(tortoise_db):
    created = await DailyRepository.create("HELLO")

    fetched = await models.Daily.get(id=created.id)
    assert fetched.hash == "HELLO"
