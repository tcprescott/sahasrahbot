"""Repository tier (Tier 3) — pure data access.

Each repository is a thin wrapper over Tortoise ORM for one domain: static async
methods performing CRUD/queries, owning ``prefetch_related``/``.values()``
choices, and returning model instances. Repositories contain no business rules,
no audit logging, no notifications, and never import a presentation framework.

Add new repositories as ``<name>_repository.py`` and export the class here.
"""

from alttprbot.repositories.audit_generated_games_repository import AuditGeneratedGamesRepository
from alttprbot.repositories.async_tournament_audit_log_repository import AsyncTournamentAuditLogRepository

__all__ = [
    "AuditGeneratedGamesRepository",
    "AsyncTournamentAuditLogRepository",
]
