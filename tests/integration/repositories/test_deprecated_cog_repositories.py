"""Round-trip tests for repositories backing the deprecated cogs (voicerole)."""

from alttprbot import models
from alttprbot.repositories import UserRepository, VoiceRoleRepository


async def test_voice_role_list_for_guild(tortoise_db):
    await models.VoiceRole.create(guild_id=1, voice_channel_id=10, role_id=100)
    await models.VoiceRole.create(guild_id=1, voice_channel_id=11, role_id=101)
    await models.VoiceRole.create(guild_id=2, voice_channel_id=12, role_id=102)

    rows = await VoiceRoleRepository.list_for_guild(1)
    assert {r.voice_channel_id for r in rows} == {10, 11}
    assert await VoiceRoleRepository.list_for_guild(99) == []


async def test_user_without_display_name_and_set(tortoise_db):
    await models.Users.create(discord_user_id=1, display_name=None)
    await models.Users.create(discord_user_id=2, display_name="HasName")

    missing = await UserRepository.list_without_display_name()
    assert [u.discord_user_id for u in missing] == [1]

    await UserRepository.set_display_name(missing[0], "NowNamed")
    assert await UserRepository.list_without_display_name() == []
