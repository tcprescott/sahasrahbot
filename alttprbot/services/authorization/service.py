"""The centralized authorization service — the single Policy Decision Point (PDP).

Owns every *domain* authorization decision in the app (tournament roles, resource
ownership, the async account-age / whitelist / RaceTime-link join policy, and the
API-key capability checks). Platform-permission gating (Discord admin / owner /
permission flags) stays native in the presentation layer; this service decides
only against the plain facts carried on an :class:`AuthSubject`.

Conventions:
- ``require_*`` methods raise :class:`PermissionError` (the message is rendered by
  the presentation error handlers), and take an optional ``message`` so each call
  site keeps its own wording.
- ``is_*`` / ``can_*`` methods return ``bool`` for callers that branch on authz.

The service never imports ``discord``/``racetime_bot``/``quart``; surfaces resolve
their platform objects into an ``AuthSubject`` first.
"""

import datetime
from typing import List, Optional

from alttprbot import models
from alttprbot.repositories import AuthorizationKeyRepository
from alttprbot.services.authorization.subject import AuthSubject

# An async-tournament participant's Discord account must be at least this much
# older than the tournament's start date (unless they are whitelisted).
ASYNC_MIN_ACCOUNT_AGE = datetime.timedelta(days=7)


class AuthorizationService:
    def __init__(self) -> None:
        self.repository = AuthorizationKeyRepository()

    # ------------------------------------------------------------------ #
    # Capability tokens (API keys) — unchanged public API                #
    # ------------------------------------------------------------------ #
    async def is_racetime_cmd_authorized(self, auth_key: str, category: str) -> bool:
        permission = await self.repository.get_permission(auth_key, "racetimecmd", category)
        return permission is not None

    async def is_api_authorized(self, auth_key: str, permission_type: str) -> bool:
        """Whether ``auth_key`` grants ``permission_type`` (any subtype)."""
        permission = await self.repository.get_by_type(auth_key, permission_type)
        return permission is not None

    # ------------------------------------------------------------------ #
    # Async tournament — role-based access (RBAC over DB grants)          #
    # ------------------------------------------------------------------ #
    async def is_async_tournament_user(
        self, subject: AuthSubject, tournament: models.AsyncTournament, roles: List[str]
    ) -> bool:
        """Whether ``subject`` holds any of ``roles`` for ``tournament``.

        ``'public'`` is granted for an inactive tournament. Otherwise the grant is
        matched against the subject's linked ``Users`` row (per-user grants) and
        their resolved Discord role ids (per-role grants). The Discord member/role
        resolution is done by the presentation subject builder, not here.
        """
        if "public" in roles and not tournament.active:
            return True
        if subject.user is None:
            return False

        from alttprbot.services.async_tournament_service import AsyncTournamentService

        service = AsyncTournamentService()
        if await service.user_has_permission(tournament, subject.user, roles):
            return True
        return await service.role_has_permission(
            tournament, list(subject.discord_role_ids), roles
        )

    async def require_async_tournament_user(
        self,
        subject: AuthSubject,
        tournament: models.AsyncTournament,
        roles: List[str],
        message: str = "You are not authorized to use this command.",
    ) -> None:
        if not await self.is_async_tournament_user(subject, tournament, roles):
            raise PermissionError(message)

    # ------------------------------------------------------------------ #
    # Async tournament — ownership (ReBAC-as-concept)                     #
    # ------------------------------------------------------------------ #
    def is_async_tournament_owner(
        self, subject: AuthSubject, tournament: models.AsyncTournament
    ) -> bool:
        return (
            subject.discord_user_id is not None
            and subject.discord_user_id == tournament.owner_id
        )

    def require_async_tournament_owner(
        self,
        subject: AuthSubject,
        tournament: models.AsyncTournament,
        message: str = "You are not the owner of this tournament.",
    ) -> None:
        if not self.is_async_tournament_owner(subject, tournament):
            raise PermissionError(message)

    def is_async_race_owner(
        self, subject: AuthSubject, race: models.AsyncTournamentRace
    ) -> bool:
        """Whether ``subject`` is the runner of ``race`` (``race.user`` prefetched)."""
        return (
            subject.discord_user_id is not None
            and race.user.discord_user_id == subject.discord_user_id
        )

    def require_async_race_owner(
        self,
        subject: AuthSubject,
        race: models.AsyncTournamentRace,
        message: str = "Only the runner of this race may do that.",
    ) -> None:
        if not self.is_async_race_owner(subject, race):
            raise PermissionError(message)

    # ------------------------------------------------------------------ #
    # Async tournament — join policy (ABAC: account age + whitelist;      #
    # capability: linked RaceTime account)                               #
    # ------------------------------------------------------------------ #
    async def require_can_join_async(
        self,
        subject: AuthSubject,
        tournament: models.AsyncTournament,
        message: str = (
            "Your Discord account is too new to participate in this tournament.  "
            "Please contact a tournament administrator for manual verification and whitelisting."
        ),
    ) -> None:
        """Enforce the account-age gate (with whitelist bypass) for joining ``tournament``."""
        if subject.account_created_at is None:
            return
        if subject.account_created_at <= (tournament.created - ASYNC_MIN_ACCOUNT_AGE):
            return

        from alttprbot.services.async_tournament_service import AsyncTournamentService

        if await AsyncTournamentService().is_user_whitelisted(tournament, subject.discord_user_id):
            return
        raise PermissionError(message)

    def require_racetime_linked(
        self,
        subject: AuthSubject,
        message: str = "You must link your RaceTime.gg account before you can do that.",
    ) -> None:
        if subject.user is None or subject.user.rtgg_id is None:
            raise PermissionError(message)

    # ------------------------------------------------------------------ #
    # Tournament — role-id config based (RBAC over TournamentDefinition)  #
    # ------------------------------------------------------------------ #
    def is_tournament_admin(self, subject: AuthSubject, definition) -> bool:
        if subject.discord_user_id in getattr(definition, "admin_user_ids", []):
            return True
        return bool(subject.discord_role_ids & set(getattr(definition, "admin_role_ids", [])))

    def require_tournament_admin(
        self,
        subject: AuthSubject,
        definition,
        message: str = "You are not a tournament administrator.",
    ) -> None:
        if not self.is_tournament_admin(subject, definition):
            raise PermissionError(message)

    def can_gatekeep(self, subject: AuthSubject, helper_role_ids) -> bool:
        return bool(subject.discord_role_ids & set(helper_role_ids or []))

    # ------------------------------------------------------------------ #
    # Resource ownership / moderation (delegated to the owning service)  #
    # ------------------------------------------------------------------ #
    def is_namespace_owner(
        self, subject: AuthSubject, namespace: models.PresetNamespaces
    ) -> bool:
        """``namespace.collaborators`` must already be fetched by the caller."""
        from alttprbot.services.preset_service import PresetService

        return PresetService.is_namespace_owner(subject.discord_user_id, namespace)

    async def is_triforce_moderator(self, subject: AuthSubject, pool_name: str) -> bool:
        from alttprbot.services.triforce_text_service import TriforceTextService

        return await TriforceTextService().is_moderator(subject.discord_user_id, pool_name)

    # ------------------------------------------------------------------ #
    # Ranked-choice elections                                            #
    # ------------------------------------------------------------------ #
    def is_election_owner(
        self, subject: AuthSubject, election: models.RankedChoiceElection
    ) -> bool:
        return (
            subject.discord_user_id is not None
            and election.owner_id == subject.discord_user_id
        )

    def can_vote_ranked_choice(
        self, subject: AuthSubject, election: models.RankedChoiceElection
    ) -> bool:
        """A public election is open to all; a private one requires the voter role."""
        if not election.private:
            return True
        return election.voter_role_id in subject.discord_role_ids

    # ------------------------------------------------------------------ #
    # RaceTime                                                            #
    # ------------------------------------------------------------------ #
    def can_roll_tournament_seed(self, subject: AuthSubject) -> bool:
        """Only entrants of the room or race monitors may roll a tournament seed."""
        return subject.is_race_monitor or subject.rtgg_id in subject.race_entrant_ids
