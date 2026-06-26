"""PresetService unit tests: ownership rules, validation, namespace creation."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from alttprbot.services import PresetService


def _namespace(owner_id, collaborator_ids=()):
    return SimpleNamespace(
        discord_user_id=owner_id,
        collaborators=[SimpleNamespace(discord_user_id=c) for c in collaborator_ids],
    )


def test_is_namespace_owner_true_for_owner():
    assert PresetService.is_namespace_owner(42, _namespace(owner_id=42)) is True


def test_is_namespace_owner_true_for_collaborator():
    ns = _namespace(owner_id=1, collaborator_ids=[7, 8])
    assert PresetService.is_namespace_owner(8, ns) is True


def test_is_namespace_owner_true_for_superuser():
    assert PresetService.is_namespace_owner(185198185990324225, _namespace(owner_id=1)) is True


def test_is_namespace_owner_false_for_stranger():
    ns = _namespace(owner_id=1, collaborator_ids=[2, 3])
    assert PresetService.is_namespace_owner(99, ns) is False


@pytest.mark.parametrize("name,valid", [
    ("open_swiss", True),
    ("ALTTPR123", True),
    ("", True),  # the original regex permits the empty string
    ("has space", False),
    ("has-dash", False),
    ("dots.bad", False),
])
def test_is_valid_preset_name(name, valid):
    assert PresetService.is_valid_preset_name(name) is valid


async def test_create_or_retrieve_namespace_slugifies_and_fetches_collaborators():
    service = PresetService()
    service.namespaces = AsyncMock()
    ns = MagicMock()
    ns.fetch_related = AsyncMock()
    service.namespaces.get_or_create_by_user.return_value = (ns, True)

    result = await service.create_or_retrieve_namespace(123, "Test User")

    assert result is ns
    service.namespaces.get_or_create_by_user.assert_awaited_once_with(
        discord_user_id=123, name="test-user"
    )
    ns.fetch_related.assert_awaited_once_with("collaborators")


async def test_get_preset_delegates_to_repository():
    service = PresetService()
    service.presets = AsyncMock()

    await service.get_preset("ns", "alttpr", "open")

    service.presets.get.assert_awaited_once_with(
        namespace_name="ns", randomizer="alttpr", preset_name="open"
    )
