"""Unit tests for the centralized AuthorizationService (the PDP).

Every decision is driven with a hand-built ``AuthSubject`` and mocked
repositories/services — no discord/quart fakes needed, which is the whole point
of routing decisions through a surface-agnostic subject.
"""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alttprbot.services import AuthorizationService, AuthSubject


def _async_tournament_service_mock(**methods):
    """Patch the lazily-imported AsyncTournamentService with a mock instance."""
    instance = MagicMock()
    for name, value in methods.items():
        setattr(instance, name, AsyncMock(return_value=value))
    return patch(
        "alttprbot.services.async_tournament_service.AsyncTournamentService",
        return_value=instance,
    )


# --- capability tokens (API keys) -------------------------------------------

async def test_is_api_authorized_maps_permission_to_bool():
    service = AuthorizationService()
    service.repository = AsyncMock()

    service.repository.get_by_type.return_value = object()
    assert await service.is_api_authorized("k", "asynctournament") is True

    service.repository.get_by_type.return_value = None
    assert await service.is_api_authorized("k", "asynctournament") is False


# --- async tournament: role-based access ------------------------------------

async def test_async_tournament_user_public_when_inactive():
    service = AuthorizationService()
    tournament = MagicMock(active=False)
    subject = AuthSubject(discord_user_id=1, user=None)
    assert await service.is_async_tournament_user(subject, tournament, ["public"]) is True


async def test_async_tournament_user_false_when_no_linked_user():
    service = AuthorizationService()
    tournament = MagicMock(active=True)
    subject = AuthSubject(discord_user_id=1, user=None)
    assert await service.is_async_tournament_user(subject, tournament, ["admin", "mod"]) is False


async def test_async_tournament_user_hits_user_permission():
    service = AuthorizationService()
    tournament = MagicMock(active=True)
    subject = AuthSubject(discord_user_id=1, user=MagicMock())
    with _async_tournament_service_mock(user_has_permission=True, role_has_permission=False):
        assert await service.is_async_tournament_user(subject, tournament, ["admin"]) is True


async def test_async_tournament_user_hits_role_permission():
    service = AuthorizationService()
    tournament = MagicMock(active=True)
    subject = AuthSubject(discord_user_id=1, user=MagicMock(), discord_role_ids=frozenset({7}))
    with _async_tournament_service_mock(user_has_permission=False, role_has_permission=True):
        assert await service.is_async_tournament_user(subject, tournament, ["mod"]) is True


async def test_async_tournament_user_denies_when_no_grant():
    service = AuthorizationService()
    tournament = MagicMock(active=True)
    subject = AuthSubject(discord_user_id=1, user=MagicMock())
    with _async_tournament_service_mock(user_has_permission=False, role_has_permission=False):
        assert await service.is_async_tournament_user(subject, tournament, ["admin"]) is False
        with pytest.raises(PermissionError, match="nope"):
            await service.require_async_tournament_user(subject, tournament, ["admin"], message="nope")


# --- async tournament / race ownership --------------------------------------

async def test_async_tournament_owner_match_and_mismatch():
    service = AuthorizationService()
    tournament = MagicMock(owner_id=42)
    assert service.is_async_tournament_owner(AuthSubject(discord_user_id=42), tournament) is True
    assert service.is_async_tournament_owner(AuthSubject(discord_user_id=99), tournament) is False
    with pytest.raises(PermissionError):
        service.require_async_tournament_owner(AuthSubject(discord_user_id=99), tournament)


async def test_async_race_owner_match_and_mismatch():
    service = AuthorizationService()
    race = MagicMock()
    race.user.discord_user_id = 42
    assert service.is_async_race_owner(AuthSubject(discord_user_id=42), race) is True
    assert service.is_async_race_owner(AuthSubject(discord_user_id=99), race) is False
    with pytest.raises(PermissionError, match="runner"):
        service.require_async_race_owner(AuthSubject(discord_user_id=99), race, message="only the runner")


# --- async join policy (age + whitelist + rtgg link) ------------------------

def _tournament_created(days_ago_for_now=None):
    created = datetime.datetime(2024, 1, 10)
    return MagicMock(created=created)


async def test_can_join_passes_for_established_account():
    service = AuthorizationService()
    tournament = _tournament_created()
    # created - 7d = 2024-01-03; an account from 2024-01-01 is old enough
    subject = AuthSubject(discord_user_id=1, account_created_at=datetime.datetime(2024, 1, 1))
    await service.require_can_join_async(subject, tournament)  # no raise


async def test_can_join_passes_when_account_age_unknown():
    service = AuthorizationService()
    await service.require_can_join_async(
        AuthSubject(discord_user_id=1, account_created_at=None), _tournament_created()
    )  # no raise


async def test_can_join_too_new_and_not_whitelisted_raises():
    service = AuthorizationService()
    tournament = _tournament_created()
    subject = AuthSubject(discord_user_id=1, account_created_at=datetime.datetime(2024, 1, 8))
    with _async_tournament_service_mock(is_user_whitelisted=False):
        with pytest.raises(PermissionError, match="too new"):
            await service.require_can_join_async(subject, tournament, message="account too new")


async def test_can_join_too_new_but_whitelisted_passes():
    service = AuthorizationService()
    tournament = _tournament_created()
    subject = AuthSubject(discord_user_id=1, account_created_at=datetime.datetime(2024, 1, 8))
    with _async_tournament_service_mock(is_user_whitelisted=True):
        await service.require_can_join_async(subject, tournament)  # no raise


async def test_require_racetime_linked():
    service = AuthorizationService()
    with pytest.raises(PermissionError):
        service.require_racetime_linked(AuthSubject(user=None))
    with pytest.raises(PermissionError):
        service.require_racetime_linked(AuthSubject(user=MagicMock(rtgg_id=None)))
    service.require_racetime_linked(AuthSubject(user=MagicMock(rtgg_id="rt1")))  # no raise


# --- tournament definition role-id checks -----------------------------------

async def test_is_tournament_admin_by_user_and_role():
    service = AuthorizationService()
    definition = MagicMock(admin_user_ids=[5], admin_role_ids=[100, 200])
    assert service.is_tournament_admin(AuthSubject(discord_user_id=5), definition) is True
    assert service.is_tournament_admin(
        AuthSubject(discord_user_id=9, discord_role_ids=frozenset({200})), definition
    ) is True
    assert service.is_tournament_admin(
        AuthSubject(discord_user_id=9, discord_role_ids=frozenset({1})), definition
    ) is False


async def test_can_gatekeep():
    service = AuthorizationService()
    assert service.can_gatekeep(AuthSubject(discord_role_ids=frozenset({3, 4})), [4, 5]) is True
    assert service.can_gatekeep(AuthSubject(discord_role_ids=frozenset({3})), [4, 5]) is False
    assert service.can_gatekeep(AuthSubject(discord_role_ids=frozenset({3})), None) is False


# --- ranked choice ----------------------------------------------------------

async def test_election_owner_and_voting():
    service = AuthorizationService()
    election = MagicMock(owner_id=7, private=False, voter_role_id=55)
    assert service.is_election_owner(AuthSubject(discord_user_id=7), election) is True
    assert service.is_election_owner(AuthSubject(discord_user_id=8), election) is False

    # public election: anyone may vote
    assert service.can_vote_ranked_choice(AuthSubject(discord_user_id=8), election) is True

    private = MagicMock(private=True, voter_role_id=55)
    assert service.can_vote_ranked_choice(
        AuthSubject(discord_role_ids=frozenset({55})), private
    ) is True
    assert service.can_vote_ranked_choice(
        AuthSubject(discord_role_ids=frozenset({1})), private
    ) is False


# --- racetime ---------------------------------------------------------------

async def test_can_roll_tournament_seed():
    service = AuthorizationService()
    assert service.can_roll_tournament_seed(AuthSubject(is_race_monitor=True)) is True
    assert service.can_roll_tournament_seed(
        AuthSubject(rtgg_id="rt1", race_entrant_ids=frozenset({"rt1"}))
    ) is True
    assert service.can_roll_tournament_seed(
        AuthSubject(rtgg_id="rt2", race_entrant_ids=frozenset({"rt1"}))
    ) is False
