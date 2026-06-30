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

from alttprbot.services.async_tournament_live_race_service import AsyncTournamentLiveRaceService
from alttprbot.services.async_tournament_permissions_service import AsyncTournamentPermissionsService
from alttprbot.services.async_tournament_scoring_service import AsyncTournamentScoringService
from alttprbot.services.async_tournament_service import AsyncTournamentService
from alttprbot.services.audit_messages_service import AuditMessagesService
from alttprbot.services.audit_service import AuditActions, AuditService
from alttprbot.services.authorization import AuthorizationService, AuthSubject
from alttprbot.services.daily_service import DailyService
from alttprbot.services.discord_server_service import DiscordServerService
from alttprbot.services.guild_config_service import GuildConfigService
from alttprbot.services.holy_image_service import HolyImageService
from alttprbot.services.inquiry_message_config_service import InquiryMessageConfigService
from alttprbot.services.konot_service import KONOTService
from alttprbot.services.nick_verification_service import NickVerificationService
from alttprbot.services.preset_service import PresetService
from alttprbot.services.race_room_service import RaceRoomService
from alttprbot.services.racer_verification_service import RacerVerificationService
from alttprbot.services.ranked_choice_service import RankedChoiceService
from alttprbot.services.reaction_role_service import ReactionRoleService
from alttprbot.services.spoiler_race_service import SpoilerRaceService
from alttprbot.services.tournament_games_service import TournamentGamesService
from alttprbot.services.tournament_results_service import TournamentResultsService
from alttprbot.services.tournament_scheduling_service import TournamentSchedulingService
from alttprbot.services.triforce_text_service import TriforceTextService
from alttprbot.services.user_service import UserService
from alttprbot.services.verified_racer_service import VerifiedRacerService
from alttprbot.services.voice_role_service import VoiceRoleService

__all__ = [
    "AsyncTournamentLiveRaceService",
    "AsyncTournamentPermissionsService",
    "AsyncTournamentScoringService",
    "AsyncTournamentService",
    "AuditActions",
    "AuditMessagesService",
    "AuditService",
    "AuthSubject",
    "AuthorizationService",
    "DailyService",
    "DiscordServerService",
    "GuildConfigService",
    "HolyImageService",
    "InquiryMessageConfigService",
    "KONOTService",
    "NickVerificationService",
    "PresetService",
    "RaceRoomService",
    "RacerVerificationService",
    "RankedChoiceService",
    "ReactionRoleService",
    "SpoilerRaceService",
    "TournamentGamesService",
    "TournamentResultsService",
    "TournamentSchedulingService",
    "TriforceTextService",
    "UserService",
    "VerifiedRacerService",
    "VoiceRoleService",
]
