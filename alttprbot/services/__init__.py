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

from alttprbot.services.audit_service import AuditActions, AuditService
from alttprbot.services.daily_service import DailyService
from alttprbot.services.discord_server_service import DiscordServerService
from alttprbot.services.guild_config_service import GuildConfigService
from alttprbot.services.preset_service import PresetService

__all__ = [
    "AuditActions",
    "AuditService",
    "DailyService",
    "DiscordServerService",
    "GuildConfigService",
    "PresetService",
]
