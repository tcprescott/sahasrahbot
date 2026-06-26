"""Repository tier (Tier 3) — pure data access.

Each repository is a thin wrapper over Tortoise ORM for one domain: static async
methods performing CRUD/queries, owning ``prefetch_related``/``.values()``
choices, and returning model instances. Repositories contain no business rules,
no audit logging, no notifications, and never import a presentation framework.

Add new repositories as ``<name>_repository.py`` and export the class here.
"""

from alttprbot.repositories.audit_generated_games_repository import AuditGeneratedGamesRepository
from alttprbot.repositories.audit_messages_repository import AuditMessagesRepository
from alttprbot.repositories.async_tournament_audit_log_repository import AsyncTournamentAuditLogRepository
from alttprbot.repositories.async_tournament_repository import AsyncTournamentRepository
from alttprbot.repositories.authorization_key_repository import AuthorizationKeyRepository
from alttprbot.repositories.daily_repository import DailyRepository
from alttprbot.repositories.discord_server_repository import DiscordServerRepository
from alttprbot.repositories.guild_config_repository import GuildConfigRepository
from alttprbot.repositories.inquiry_message_config_repository import InquiryMessageConfigRepository
from alttprbot.repositories.nick_verification_repository import NickVerificationRepository
from alttprbot.repositories.preset_namespace_repository import PresetNamespaceRepository
from alttprbot.repositories.preset_repository import PresetRepository
from alttprbot.repositories.race_room_repository import RaceRoomRepository
from alttprbot.repositories.racer_verification_repository import RacerVerificationRepository
from alttprbot.repositories.ranked_choice_repository import RankedChoiceRepository
from alttprbot.repositories.scheduled_events_repository import ScheduledEventsRepository
from alttprbot.repositories.spoiler_race_repository import SpoilerRaceRepository
from alttprbot.repositories.tournament_games_repository import TournamentGamesRepository
from alttprbot.repositories.tournament_preset_history_repository import TournamentPresetHistoryRepository
from alttprbot.repositories.tournament_results_repository import TournamentResultsRepository
from alttprbot.repositories.triforce_text_repository import TriforceTextRepository
from alttprbot.repositories.user_repository import UserRepository
from alttprbot.repositories.verified_racer_repository import VerifiedRacerRepository

__all__ = [
    "AuditGeneratedGamesRepository",
    "AuditMessagesRepository",
    "AsyncTournamentAuditLogRepository",
    "AsyncTournamentRepository",
    "AuthorizationKeyRepository",
    "DailyRepository",
    "DiscordServerRepository",
    "GuildConfigRepository",
    "InquiryMessageConfigRepository",
    "NickVerificationRepository",
    "PresetNamespaceRepository",
    "PresetRepository",
    "RaceRoomRepository",
    "RacerVerificationRepository",
    "RankedChoiceRepository",
    "ScheduledEventsRepository",
    "SpoilerRaceRepository",
    "TournamentGamesRepository",
    "TournamentPresetHistoryRepository",
    "TournamentResultsRepository",
    "TriforceTextRepository",
    "UserRepository",
    "VerifiedRacerRepository",
]
