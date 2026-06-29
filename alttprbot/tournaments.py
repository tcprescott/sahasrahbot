import json
import logging

import aiohttp

import config
from alttprbot import models
from alttprbot.tournament import test, boots, dailies, smwde, smrl_playoff, nologic, alttprhmg, alttprleague, alttprmini, alttprde, alttpr_quals
from alttprbot.tournament import registry_loader
from alttprbot.tournament.orchestrator_adapter import make_adapter
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
from alttprbot.presentation.racetime import bot as racetimebot

RACETIME_URL = config.RACETIME_URL

# Phase 0: AVAILABLE_TOURNAMENT_HANDLERS capability catalog
# This represents what handlers exist in the codebase, not what is active.
# Active handlers are determined by TOURNAMENT_DATA (hardcoded fallback)
# or by config/tournaments.yaml when TOURNAMENT_CONFIG_ENABLED is true.
AVAILABLE_TOURNAMENT_HANDLERS = {
    # Migrated to the decomposed orchestrator/presenter (see
    # docs/plans/tournament_decomposition.md): 'test' (debug), 'boots' (first seed-rolling),
    # the trivial/low ALTTPR tail 'smwde'/'nologic'/'alttprhmg'/'alttprde'/'alttprmini', the
    # moderate league handlers 'invleague'/'alttprleague' (one orchestrator, two configs), and
    # 'smrl' (SM playoffs — custom SM seed flow + settings-submission form).
    # Remaining slugs keep their legacy god-object class until migrated one-per-PR.
    'test': make_adapter(TestOrchestrator, TEST_DEFINITION),
    'alttpr': make_adapter(ALTTPRQualifierOrchestrator, QUALIFIER_DEFINITION),
    'alttprdaily': make_adapter(AlttprSGDailyOrchestrator, ALTTPR_DAILY_DEFINITION),
    'smz3': make_adapter(SMZ3DailyOrchestrator, SMZ3_DAILY_DEFINITION),
    'invleague': make_adapter(ALTTPRLeagueOrchestrator, INVITATIONAL_LEAGUE_DEFINITION),
    'alttprleague': make_adapter(ALTTPRLeagueOrchestrator, OPEN_LEAGUE_DEFINITION),
    'boots': make_adapter(BootsOrchestrator, BOOTS_DEFINITION),
    'nologic': make_adapter(NoLogicOrchestrator, NOLOGIC_DEFINITION),
    'smwde': make_adapter(SMWDEOrchestrator, SMWDE_DEFINITION),
    'alttprhmg': make_adapter(ALTTPRHMGOrchestrator, ALTTPRHMG_DEFINITION),
    'alttprmini': make_adapter(ALTTPRMiniOrchestrator, ALTTPRMINI_DEFINITION),
    'alttprde': make_adapter(ALTTPRDEOrchestrator, ALTTPRDE_DEFINITION),
    'smrl': make_adapter(SMRLPlayoffsOrchestrator, SMRL_DEFINITION),
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
# All active handlers are now decomposed orchestrators (no legacy god-objects remain active).
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


# Phase 1: Dual-path runtime switch
# Build active registry from config if TOURNAMENT_CONFIG_ENABLED is true,
# otherwise use hardcoded TOURNAMENT_DATA as fallback.
def _initialize_tournament_registry():
    """
    Initialize tournament registry based on TOURNAMENT_CONFIG_ENABLED flag.
    
    If config is enabled, loads from config/tournaments.yaml.
    Otherwise, uses hardcoded TOURNAMENT_DATA as fallback.
    
    Returns active registry and logs source/profile/enabled handlers.
    """
    # Check if config-driven registry is enabled
    config_enabled = getattr(config, 'TOURNAMENT_CONFIG_ENABLED', False)
    
    if config_enabled:
        # Phase 1: Config-backed path
        try:
            # Load and validate configuration
            tournament_config = registry_loader.load_tournament_config(
                available_handlers=AVAILABLE_TOURNAMENT_HANDLERS
            )
            
            # Select profile based on DEBUG flag
            profile_name = 'debug' if config.DEBUG else 'production'
            
            # Build active registry from enabled events
            active_registry = registry_loader.build_active_registry(
                registry=tournament_config,
                available_handlers=AVAILABLE_TOURNAMENT_HANDLERS,
                profile_name=profile_name
            )
            
            # Log summary
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
        # Phase 1: Hardcoded fallback path (default)
        profile_name = 'debug' if config.DEBUG else 'production'
        enabled_events = list(_HARDCODED_TOURNAMENT_DATA.keys())
        
        logging.info(
            f"Tournament Registry: source=hardcoded, profile={profile_name}, "
            f"enabled_events_count={len(enabled_events)}, "
            f"enabled_event_slugs={enabled_events}"
        )
        
        return _HARDCODED_TOURNAMENT_DATA


# Initialize the active tournament registry at module load time
TOURNAMENT_DATA = _initialize_tournament_registry()


async def fetch_tournament_handler(event, episodeid: int, rtgg_handler=None):
    return await TOURNAMENT_DATA[event].construct(episodeid, rtgg_handler)


async def fetch_tournament_handler_v2(event, episode: dict, rtgg_handler=None):
    return await TOURNAMENT_DATA[event].construct_with_episode_data(episode, rtgg_handler)


async def create_tournament_race_room(event, episodeid):
    event_data = await TOURNAMENT_DATA[event].get_config()
    rtgg_bot = racetimebot.racetime_bots[event_data.data.racetime_category]
    race = await models.TournamentResults.get_or_none(episode_id=episodeid)
    if race:
        async with aiohttp.request(method='get', url=rtgg_bot.http_uri(f"/{race.srl_id}/data"),
                                   raise_for_status=True) as resp:
            race_data = json.loads(await resp.read())
        status = race_data.get('status', {}).get('value')
        if not status == 'cancelled':
            return
        await race.delete()

    handler = await TOURNAMENT_DATA[event].construct_race_room(episodeid)
    return handler
