"""Repository round-trip tests against an in-memory SQLite database.

See alttprbot/repositories/audit_generated_games_repository.py.
"""

from alttprbot import models
from alttprbot.repositories import AuditGeneratedGamesRepository


async def test_record_persists_all_fields(tortoise_db):
    created = await AuditGeneratedGamesRepository.record(
        randomizer="alttpr",
        hash_id="ABCDE",
        permalink="https://alttpr.com/h/ABCDE",
        settings={"glitches": "none"},
        gentype="preset",
        genoption="open",
    )

    fetched = await models.AuditGeneratedGames.get(id=created.id)
    assert fetched.randomizer == "alttpr"
    assert fetched.hash_id == "ABCDE"
    assert fetched.permalink == "https://alttpr.com/h/ABCDE"
    assert fetched.settings == {"glitches": "none"}
    assert fetched.gentype == "preset"
    assert fetched.genoption == "open"
    # doors/avianart are model-level defaults; customizer == 0 comes from the
    # repository's parameter default (the model field is IntField(null=True)).
    assert fetched.customizer == 0
    assert fetched.doors is False
    assert fetched.avianart is False


async def test_record_honours_optional_overrides(tortoise_db):
    created = await AuditGeneratedGamesRepository.record(
        randomizer="alttprdoors",
        hash_id="ZZZ",
        permalink="https://example/p",
        settings=None,
        gentype="mystery",
        genoption=None,
        customizer=1,
        doors=True,
        avianart=True,
    )

    fetched = await models.AuditGeneratedGames.get(id=created.id)
    assert fetched.settings is None
    assert fetched.genoption is None
    assert fetched.customizer == 1
    assert fetched.doors is True
    assert fetched.avianart is True
