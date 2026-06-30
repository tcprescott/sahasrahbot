"""DiscordServerRepository round-trip tests against in-memory SQLite.

See alttprbot/repositories/discord_server_repository.py.
"""

from alttprbot.repositories import DiscordServerRepository


async def test_category_crud_round_trip(tortoise_db):
    created = await DiscordServerRepository.create_category(
        guild_id=10,
        channel_id=20,
        category_title="Racing",
        category_description="desc",
        order=1,
    )
    assert created.category_title == "Racing"

    listed = await DiscordServerRepository.list_categories(10)
    assert [c.id for c in listed] == [created.id]

    updated = await DiscordServerRepository.update_category(
        created.id,
        category_title="Renamed",
        category_description=None,
        order=2,
    )
    assert updated == 1
    refetched = (await DiscordServerRepository.list_categories(10))[0]
    assert refetched.category_title == "Renamed"
    assert refetched.category_description is None
    assert refetched.order == 2

    deleted = await DiscordServerRepository.delete_category(created.id)
    assert deleted == 1
    assert await DiscordServerRepository.list_categories(10) == []


async def test_server_crud_and_prefetch(tortoise_db):
    category = await DiscordServerRepository.create_category(
        guild_id=10,
        channel_id=20,
        category_title="Racing",
    )

    server = await DiscordServerRepository.create_server(
        invite_id="inv123",
        category_id=category.id,
        server_description="My Server",
    )
    assert server.server_description == "My Server"

    servers = await DiscordServerRepository.list_servers(category.id)
    assert [s.id for s in servers] == [server.id]

    # prefetch exposes the reverse relation used by the cog's refresh command
    with_servers = await DiscordServerRepository.list_categories_with_servers(10)
    assert len(with_servers) == 1
    assert [s.id for s in with_servers[0].server_list] == [server.id]

    await DiscordServerRepository.update_server(
        server.id,
        invite_id="inv999",
        category_id=category.id,
        server_description="Renamed Server",
    )
    refetched = (await DiscordServerRepository.list_servers(category.id))[0]
    assert refetched.invite_id == "inv999"
    assert refetched.server_description == "Renamed Server"

    deleted = await DiscordServerRepository.delete_server(server.id)
    assert deleted == 1
    assert await DiscordServerRepository.list_servers(category.id) == []
