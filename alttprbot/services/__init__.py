"""Service tier (Tier 2) — business logic.

Services enforce rules and validation, coordinate repositories, write audit
logs, and enqueue notifications. They are instantiated fresh per call and inject
their repositories in ``__init__``. Services raise ``ValueError`` for user-input
errors, ``PermissionError`` for authorization failures, and existing
``SahasrahBotException`` subclasses for domain errors. A service must never
import ``discord``, ``racetime_bot``, ``quart``, or ``alttprbot.presentation``.

Add new services as ``<name>_service.py`` (or a domain subpackage) and export the
class here.
"""

from alttprbot.services.async_tournament_service import AsyncTournamentService
from alttprbot.services.audit_service import AuditActions, AuditService
from alttprbot.services.authorization_service import AuthorizationService
from alttprbot.services.daily_service import DailyService
from alttprbot.services.discord_server_service import DiscordServerService
from alttprbot.services.guild_config_service import GuildConfigService
from alttprbot.services.nick_verification_service import NickVerificationService
from alttprbot.services.preset_service import PresetService
from alttprbot.services.race_room_service import RaceRoomService
from alttprbot.services.ranked_choice_service import RankedChoiceService
from alttprbot.services.spoiler_race_service import SpoilerRaceService
from alttprbot.services.tournament_games_service import TournamentGamesService
from alttprbot.services.tournament_results_service import TournamentResultsService
from alttprbot.services.triforce_text_service import TriforceTextService
from alttprbot.services.user_service import UserService

__all__ = [
    "AsyncTournamentService",
    "AuditActions",
    "AuditService",
    "AuthorizationService",
    "DailyService",
    "DiscordServerService",
    "GuildConfigService",
    "NickVerificationService",
    "PresetService",
    "RaceRoomService",
    "RankedChoiceService",
    "SpoilerRaceService",
    "TournamentGamesService",
    "TournamentResultsService",
    "TriforceTextService",
    "UserService",
]
