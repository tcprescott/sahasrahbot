"""Round-trip tests for the preset repositories against in-memory SQLite.

See alttprbot/repositories/preset_repository.py and preset_namespace_repository.py.
"""

from alttprbot import models
from alttprbot.repositories import PresetNamespaceRepository, PresetRepository


async def test_namespace_get_or_create_and_lookup(tortoise_db):
    ns, created = await PresetNamespaceRepository.get_or_create_by_user(
        discord_user_id=555, name="myns"
    )
    assert created is True

    again, created_again = await PresetNamespaceRepository.get_or_create_by_user(
        discord_user_id=555, name="ignored"
    )
    assert created_again is False
    assert again.id == ns.id

    found = await PresetNamespaceRepository.get_by_name("myns")
    assert found is not None and found.id == ns.id
    assert await PresetNamespaceRepository.get_by_name("missing") is None


async def test_preset_upsert_get_list_delete(tortoise_db):
    ns = await models.PresetNamespaces.create(discord_user_id=1, name="ns1")

    created, was_created = await PresetRepository.upsert(
        namespace=ns, randomizer="alttpr", preset_name="open", content="a: 1"
    )
    assert was_created is True
    assert created.content == "a: 1"

    # upsert again updates content in place (no new row)
    updated, was_created2 = await PresetRepository.upsert(
        namespace=ns, randomizer="alttpr", preset_name="open", content="a: 2"
    )
    assert was_created2 is False
    assert updated.id == created.id
    assert updated.content == "a: 2"

    fetched = await PresetRepository.get(namespace_name="ns1", randomizer="alttpr", preset_name="open")
    assert fetched is not None and fetched.content == "a: 2"

    assert await PresetRepository.list_preset_names(namespace_name="ns1", randomizer="alttpr") == ["open"]
    assert await PresetRepository.list_preset_names(namespace_name="ns1", randomizer="smz3") == []

    await PresetRepository.delete_instance(fetched)
    assert await PresetRepository.get(namespace_name="ns1", randomizer="alttpr", preset_name="open") is None


async def test_list_all_namespaces_with_presets_for_randomizer(tortoise_db):
    ns1 = await models.PresetNamespaces.create(discord_user_id=1, name="ns1")
    ns2 = await models.PresetNamespaces.create(discord_user_id=2, name="ns2")
    await PresetRepository.upsert(namespace=ns1, randomizer="alttpr", preset_name="open", content="x")
    await PresetRepository.upsert(namespace=ns2, randomizer="smz3", preset_name="hard", content="y")

    results = await PresetNamespaceRepository.list_all_with_presets_for_randomizer("alttpr")
    by_name = {n.name: [p.preset_name for p in n.presets] for n in results}
    assert by_name == {"ns1": ["open"], "ns2": []}
