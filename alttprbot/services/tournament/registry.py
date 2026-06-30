"""Service-tier tournament registry.

The single source of truth for which tournament handler drives each event slug. Every
slug maps to a :class:`TournamentEntry` (an orchestrator class + its definition) — pure
service-tier data with **no presentation dependency**. The presentation tier
(``presentation/discord/tournament/dispatch.py``) reads ``TOURNAMENT_DATA`` and builds a
``TournamentCoordinator`` to drive a live event.

The active set is resolved at import time from either the hardcoded fallback (the
production default) or ``config/tournaments.yaml`` when ``TOURNAMENT_CONFIG_ENABLED`` is
true. Both paths resolve the handler through ``AVAILABLE_TOURNAMENT_HANDLERS``, so the
catalog is the single source — the fallback only selects *which* slugs are active, never
which class drives them.
"""

import logging
from dataclasses import dataclass

import config
from alttprbot.services.tournament import registry_loader
from alttprbot.services.tournament.definition import TournamentDefinition
from alttprbot.services.tournament.test import TEST_DEFINITION, TestOrchestrator
from alttprbot.services.tournament.boots import BOOTS_DEFINITION, BootsOrchestrator
from alttprbot.services.tournament.smwde import SMWDE_DEFINITION, SMWDEOrchestrator
from alttprbot.services.tournament.nologic import NOLOGIC_DEFINITION, NoLogicOrchestrator
from alttprbot.services.tournament.alttprhmg import ALTTPRHMG_DEFINITION, ALTTPRHMGOrchestrator
from alttprbot.services.tournament.alttprde import ALTTPRDE_DEFINITION, ALTTPRDEOrchestrator
from alttprbot.services.tournament.alttprmini import ALTTPRMINI_DEFINITION, ALTTPRMiniOrchestrator
from alttprbot.services.tournament.alttprleague import (
    INVITATIONAL_LEAGUE_DEFINITION,
    OPEN_LEAGUE_DEFINITION,
    ALTTPRLeagueOrchestrator,
)
from alttprbot.services.tournament.smrl import SMRL_DEFINITION, SMRLPlayoffsOrchestrator
from alttprbot.services.tournament.dailies import (
    ALTTPR_DAILY_DEFINITION,
    SMZ3_DAILY_DEFINITION,
    AlttprSGDailyOrchestrator,
    SMZ3DailyOrchestrator,
)
from alttprbot.services.tournament.alttpr_quals import QUALIFIER_DEFINITION, ALTTPRQualifierOrchestrator


@dataclass(frozen=True)
class TournamentEntry:
    """A registry entry binding an orchestrator class to its tournament definition."""
    orchestrator_cls: type
    definition: TournamentDefinition


# AVAILABLE_TOURNAMENT_HANDLERS capability catalog.
# This represents what handlers exist in the codebase, not what is active. Active handlers
# are determined by TOURNAMENT_DATA (the hardcoded fallback) or by config/tournaments.yaml
# when TOURNAMENT_CONFIG_ENABLED is true.
AVAILABLE_TOURNAMENT_HANDLERS = {
    'test': TournamentEntry(TestOrchestrator, TEST_DEFINITION),
    'alttpr': TournamentEntry(ALTTPRQualifierOrchestrator, QUALIFIER_DEFINITION),
    'alttprdaily': TournamentEntry(AlttprSGDailyOrchestrator, ALTTPR_DAILY_DEFINITION),
    'smz3': TournamentEntry(SMZ3DailyOrchestrator, SMZ3_DAILY_DEFINITION),
    'invleague': TournamentEntry(ALTTPRLeagueOrchestrator, INVITATIONAL_LEAGUE_DEFINITION),
    'alttprleague': TournamentEntry(ALTTPRLeagueOrchestrator, OPEN_LEAGUE_DEFINITION),
    'boots': TournamentEntry(BootsOrchestrator, BOOTS_DEFINITION),
    'nologic': TournamentEntry(NoLogicOrchestrator, NOLOGIC_DEFINITION),
    'smwde': TournamentEntry(SMWDEOrchestrator, SMWDE_DEFINITION),
    'alttprhmg': TournamentEntry(ALTTPRHMGOrchestrator, ALTTPRHMG_DEFINITION),
    'alttprmini': TournamentEntry(ALTTPRMiniOrchestrator, ALTTPRMINI_DEFINITION),
    'alttprde': TournamentEntry(ALTTPRDEOrchestrator, ALTTPRDE_DEFINITION),
    'smrl': TournamentEntry(SMRLPlayoffsOrchestrator, SMRL_DEFINITION),
}

# Hardcoded registry fallback (active when TOURNAMENT_CONFIG_ENABLED is false — the
# production default). Single source of truth: the *handler* for every slug always comes
# from AVAILABLE_TOURNAMENT_HANDLERS, so this fallback can never drift from the catalog (or
# the config/tournaments.yaml path) — migrating a handler in the catalog propagates to both
# paths automatically. These lists declare only *which* slugs are active per profile.
#
# Seasonal handlers are decomposed in the catalog but left inactive here; add a slug to the
# production list to enable it for a season:
#   boots, nologic, smwde, alttprhmg, alttprmini, alttprde, smrl
if config.DEBUG:
    # Debug: no auto-active tournaments (enable 'test' here manually when needed).
    _HARDCODED_ACTIVE_SLUGS = []
else:
    _HARDCODED_ACTIVE_SLUGS = [
        'alttpr',         # ALTTPR main-tournament live qualifier (decomposed orchestrator)
        'alttprdaily',    # ALTTPR daily series (decomposed orchestrator)
        'smz3',           # SMZ3 weekly (decomposed orchestrator)
        'invleague',      # ALTTPR Invitational League (decomposed orchestrator)
        'alttprleague',   # ALTTPR Open League (decomposed orchestrator)
    ]

_HARDCODED_TOURNAMENT_DATA = {
    slug: AVAILABLE_TOURNAMENT_HANDLERS[slug] for slug in _HARDCODED_ACTIVE_SLUGS
}


def _initialize_tournament_registry():
    """Resolve the active tournament registry based on the TOURNAMENT_CONFIG_ENABLED flag.

    If config is enabled, loads from config/tournaments.yaml; otherwise uses the hardcoded
    fallback. Returns ``{slug: TournamentEntry}`` and logs the source/profile/enabled set.
    """
    config_enabled = getattr(config, 'TOURNAMENT_CONFIG_ENABLED', False)

    if config_enabled:
        # Config-backed path
        try:
            tournament_config = registry_loader.load_tournament_config(
                available_handlers=AVAILABLE_TOURNAMENT_HANDLERS
            )

            profile_name = 'debug' if config.DEBUG else 'production'

            active_registry = registry_loader.build_active_registry(
                registry=tournament_config,
                available_handlers=AVAILABLE_TOURNAMENT_HANDLERS,
                profile_name=profile_name
            )

            registry_loader.log_registry_summary(
                registry=tournament_config,
                profile_name=profile_name,
                active_registry=active_registry
            )

            logging.info(f"Tournament registry loaded from config: profile={profile_name}")

            return active_registry

        except registry_loader.TournamentConfigError as e:
            # Fatal error: invalid config should fail before operational loops begin
            logging.error(f"FATAL: Tournament config validation failed: {e}")
            logging.error("Tournament loops will not start. Fix config and restart.")
            raise

    else:
        # Hardcoded fallback path (default)
        profile_name = 'debug' if config.DEBUG else 'production'
        enabled_events = list(_HARDCODED_TOURNAMENT_DATA.keys())

        logging.info(
            f"Tournament Registry: source=hardcoded, profile={profile_name}, "
            f"enabled_events_count={len(enabled_events)}, "
            f"enabled_event_slugs={enabled_events}"
        )

        return _HARDCODED_TOURNAMENT_DATA


# Resolve the active tournament registry at module load time.
TOURNAMENT_DATA = _initialize_tournament_registry()
