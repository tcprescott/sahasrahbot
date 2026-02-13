import json
import logging

import aiohttp

import config
from alttprbot import models
from alttprbot.tournament import test, boots, dailies, smwde, smrl_playoff, nologic, alttprhmg, alttprleague, alttprmini, alttprde, alttpr_quals
from alttprbot.tournament import registry_loader
from alttprbot_racetime import bot as racetimebot

RACETIME_URL = config.RACETIME_URL

# Phase 0: AVAILABLE_TOURNAMENT_HANDLERS capability catalog
# This represents what handlers exist in the codebase, not what is active.
# Active handlers are determined by TOURNAMENT_DATA (hardcoded fallback)
# or by config/tournaments.yaml when TOURNAMENT_CONFIG_ENABLED is true.
AVAILABLE_TOURNAMENT_HANDLERS = {
    'test': test.TestTournament,
    'alttpr': alttpr_quals.ALTTPRQualifierRace,
    'alttprdaily': dailies.AlttprSGDailyRace,
    'smz3': dailies.SMZ3DailyRace,
    'invleague': alttprleague.ALTTPRLeague,
    'alttprleague': alttprleague.ALTTPROpenLeague,
    'boots': boots.ALTTPRCASBootsTournamentRace,
    'nologic': nologic.ALTTPRNoLogicRace,
    'smwde': smwde.SMWDETournament,
    'alttprhmg': alttprhmg.ALTTPRHMGTournament,
    'alttprmini': alttprmini.ALTTPRMiniTournament,
    'alttprde': alttprde.ALTTPRDETournament,
    'smrl': smrl_playoff.SMRLPlayoffs,
}

# Phase 1: Hardcoded registry fallback (preserved for rollback safety)
# This is the original registry logic, kept as emergency fallback.
# Active when TOURNAMENT_CONFIG_ENABLED is false (default).
if config.DEBUG:
    _HARDCODED_TOURNAMENT_DATA = {
        'test': test.TestTournament
    }
else:
    _HARDCODED_TOURNAMENT_DATA = {
        # REGULAR TOURNAMENTS

        # 'alttprcd': alttprcd.ALTTPRCDTournament,
        # 'alttprde': alttprde.ALTTPRDETournament,
        # 'alttprmini': alttprmini.ALTTPRMiniTournament,
        'alttpr': alttpr_quals.ALTTPRQualifierRace,
        # 'boots': boots.ALTTPRCASBootsTournamentRace,
        # 'nologic': nologic.ALTTPRNoLogicRace,
        # 'smwde': smwde.SMWDETournament,
        # 'alttprfr': alttprfr.ALTTPRFRTournament,
        # 'alttprhmg': alttprhmg.ALTTPRHMGTournament,
        # 'alttpres': alttpres.ALTTPRESTournament,
        # 'smz3coop': smz3coop.SMZ3CoopTournament,
        # 'smbingo': smbingo.SMBingoTournament,
        # 'smrl': smrl_playoff.SMRLPlayoffs,
        # 'sgl24alttpr': alttprsglive.ALTTPRSGLive,

        # Dailies/Weeklies
        'alttprdaily': dailies.AlttprSGDailyRace,
        'smz3': dailies.SMZ3DailyRace,

        # ALTTPR League
        'invleague': alttprleague.ALTTPRLeague,
        'alttprleague': alttprleague.ALTTPROpenLeague,
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
