"""Round-trip tests for KONOTRepository against in-memory SQLite."""

from alttprbot.repositories import KONOTRepository


async def test_konot_game_and_segment_round_trip(tortoise_db):
    game = await KONOTRepository.create_game("test")
    assert game.category_slug == "test"
    assert await KONOTRepository.get_game(game.id) is not None

    segment = await KONOTRepository.create_segment(
        racetime_room="test/room-1", game_id=game.id, segment_number=1
    )
    assert segment.segment_number == 1

    fetched = await KONOTRepository.get_segment_by_room("test/room-1")
    assert fetched is not None and fetched.game_id == game.id
    assert await KONOTRepository.get_segment_by_room("nope") is None
