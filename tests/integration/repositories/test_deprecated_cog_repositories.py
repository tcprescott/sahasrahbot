"""Round-trip tests for repositories backing the deprecated cogs (voicerole/smmulti/admin)."""

from alttprbot import models
from alttprbot.repositories import MultiworldRepository, UserRepository, VoiceRoleRepository


async def test_voice_role_list_for_guild(tortoise_db):
    await models.VoiceRole.create(guild_id=1, voice_channel_id=10, role_id=100)
    await models.VoiceRole.create(guild_id=1, voice_channel_id=11, role_id=101)
    await models.VoiceRole.create(guild_id=2, voice_channel_id=12, role_id=102)

    rows = await VoiceRoleRepository.list_for_guild(1)
    assert {r.voice_channel_id for r in rows} == {10, 11}
    assert await VoiceRoleRepository.list_for_guild(99) == []


async def test_multiworld_and_entrants_round_trip(tortoise_db):
    mw = await models.Multiworld.create(message_id=555, owner_id=1, status="OPEN")
    assert (await MultiworldRepository.get_by_message_id(555)).owner_id == 1
    assert await MultiworldRepository.get_by_message_id(999) is None

    assert await MultiworldRepository.get_entrant(42, mw) is None
    entrant = await MultiworldRepository.create_entrant(42, mw)
    assert (await MultiworldRepository.get_entrant(42, mw)).id == entrant.id

    listed = await MultiworldRepository.list_entrants_by_message_id(555)
    assert [e.discord_user_id for e in listed] == [42]

    await MultiworldRepository.delete_entrant(entrant)
    assert await MultiworldRepository.get_entrant(42, mw) is None


async def test_user_without_display_name_and_set(tortoise_db):
    await models.Users.create(discord_user_id=1, display_name=None)
    await models.Users.create(discord_user_id=2, display_name="HasName")

    missing = await UserRepository.list_without_display_name()
    assert [u.discord_user_id for u in missing] == [1]

    await UserRepository.set_display_name(missing[0], "NowNamed")
    assert await UserRepository.list_without_display_name() == []
