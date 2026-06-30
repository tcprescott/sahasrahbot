"""Unit tests for service methods added for the cog burn-down (repos mocked)."""

from unittest.mock import AsyncMock, sentinel

from alttprbot.services import (
    AuditService,
    AuthorizationService,
    NickVerificationService,
    PresetService,
)


async def test_is_api_authorized_maps_presence_to_bool():
    service = AuthorizationService()
    service.repository = AsyncMock()

    service.repository.get_by_type.return_value = object()
    assert await service.is_api_authorized("k", "asynctournament") is True
    service.repository.get_by_type.assert_awaited_once_with("k", "asynctournament")

    service.repository.get_by_type.return_value = None
    assert await service.is_api_authorized("k", "asynctournament") is False


async def test_get_generated_game_by_hash_id_delegates():
    service = AuditService()
    service.generated_games_repository = AsyncMock()
    service.generated_games_repository.get_by_hash_id.return_value = sentinel.game

    assert await service.get_generated_game_by_hash_id("ABCDE") is sentinel.game
    service.generated_games_repository.get_by_hash_id.assert_awaited_once_with("ABCDE")


async def test_preset_delete_namespaces_for_user_delegates():
    service = PresetService()
    service.namespaces = AsyncMock()
    service.namespaces.delete_by_discord_id.return_value = 2

    assert await service.delete_namespaces_for_user(42) == 2
    service.namespaces.delete_by_discord_id.assert_awaited_once_with(42)


async def test_nick_verification_delete_for_user_delegates():
    service = NickVerificationService()
    service.repository = AsyncMock()
    service.repository.delete_by_discord_id.return_value = 1

    assert await service.delete_for_user(42) == 1
    service.repository.delete_by_discord_id.assert_awaited_once_with(42)
