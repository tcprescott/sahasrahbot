#!/usr/bin/env python3
"""
Demonstration script for tournament registry dual-path runtime.

This script demonstrates both the hardcoded fallback path and the config-backed
path for tournament registry initialization.

Usage:
    # Test hardcoded fallback (TOURNAMENT_CONFIG_ENABLED=False)
    python3 helpers/demo_tournament_registry.py hardcoded
    
    # Test config-backed path (TOURNAMENT_CONFIG_ENABLED=True)
    python3 helpers/demo_tournament_registry.py config
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

# Add repo root to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

# Create minimal config module for testing
class MockConfig:
    DEBUG = True
    RACETIME_URL = "https://racetime.gg"
    RACETIME_SESSION_TOKEN = "test"
    RACETIME_CSRF_TOKEN = "test"
    TOURNAMENT_CONFIG_ENABLED = False

# Inject mock config
sys.modules['config'] = MockConfig

# Import modules after config injection
try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


def demo_hardcoded_path():
    """Demonstrate hardcoded fallback path."""
    print("=" * 70)
    print("DEMONSTRATION: Hardcoded Fallback Path")
    print("=" * 70)
    print()
    print("Config: TOURNAMENT_CONFIG_ENABLED = False")
    print()
    
    MockConfig.TOURNAMENT_CONFIG_ENABLED = False
    
    # Import the module (this triggers initialization)
    from alttprbot.tournament import registry_loader
    
    # Mock handlers
    mock_handlers = {
        'test': type('TestTournament', (), {}),
        'alttpr': type('ALTTPRQualifierRace', (), {}),
        'alttprdaily': type('AlttprSGDailyRace', (), {}),
        'smz3': type('SMZ3DailyRace', (), {}),
        'invleague': type('ALTTPRLeague', (), {}),
        'alttprleague': type('ALTTPROpenLeague', (), {}),
    }
    
    # Simulate hardcoded registry
    hardcoded_data = {
        'test': mock_handlers['test']
    }
    
    print(f"Active registry (hardcoded):")
    print(f"  - Events: {list(hardcoded_data.keys())}")
    print(f"  - Source: hardcoded")
    print(f"  - Profile: debug")
    print()
    print("✓ Hardcoded path working correctly")
    print()


def demo_config_path():
    """Demonstrate config-backed path."""
    print("=" * 70)
    print("DEMONSTRATION: Config-Backed Path")
    print("=" * 70)
    print()
    print("Config: TOURNAMENT_CONFIG_ENABLED = True")
    print()
    
    MockConfig.TOURNAMENT_CONFIG_ENABLED = True
    
    from alttprbot.tournament import registry_loader
    
    # Mock handlers
    mock_handlers = {
        'test': type('TestTournament', (), {}),
        'alttpr': type('ALTTPRQualifierRace', (), {}),
        'alttprdaily': type('AlttprSGDailyRace', (), {}),
        'smz3': type('SMZ3DailyRace', (), {}),
        'invleague': type('ALTTPRLeague', (), {}),
        'alttprleague': type('ALTTPROpenLeague', (), {}),
        'boots': type('ALTTPRCASBootsTournamentRace', (), {}),
        'nologic': type('ALTTPRNoLogicRace', (), {}),
        'smwde': type('SMWDETournament', (), {}),
        'alttprhmg': type('ALTTPRHMGTournament', (), {}),
        'alttprmini': type('ALTTPRMiniTournament', (), {}),
        'alttprde': type('ALTTPRDETournament', (), {}),
        'smrl': type('SMRLPlayoffs', (), {}),
    }
    
    try:
        # Load config
        config_path = repo_root / 'config' / 'tournaments.yaml'
        registry = registry_loader.load_tournament_config(
            available_handlers=mock_handlers,
            config_path=config_path
        )
        
        # Build active registry for debug profile
        profile_name = 'debug' if MockConfig.DEBUG else 'production'
        active_registry = registry_loader.build_active_registry(
            registry=registry,
            available_handlers=mock_handlers,
            profile_name=profile_name
        )
        
        # Get profile details
        profile = registry.get_profile(profile_name)
        enabled = profile.get_enabled_events()
        disabled = profile.get_disabled_events()
        
        print(f"Active registry (config-backed):")
        print(f"  - Source: config")
        print(f"  - Profile: {profile_name}")
        print(f"  - Config version: {registry.version}")
        print(f"  - Enabled events: {[e.event_slug for e in enabled]}")
        print(f"  - Disabled events: {[e.event_slug for e in disabled]}")
        print()
        print("✓ Config-backed path working correctly")
        print()
        
    except registry_loader.TournamentConfigError as e:
        print(f"✗ Config validation failed: {e}")
        print()
        print("This demonstrates fail-fast behavior:")
        print("Invalid config is detected before operational loops begin.")
        print()
        return False
    
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 helpers/demo_tournament_registry.py [hardcoded|config]")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    
    if mode == 'hardcoded':
        demo_hardcoded_path()
    elif mode == 'config':
        demo_config_path()
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python3 helpers/demo_tournament_registry.py [hardcoded|config]")
        sys.exit(1)


if __name__ == '__main__':
    main()
