#!/usr/bin/env python3
"""
Standalone validation script for tournament registry config rollout.

This script validates the tournament registry configuration without requiring
the full application dependencies. It can be run as part of CI/CD or during
development to ensure the configuration is valid.

Usage:
    python3 helpers/validate_tournament_config.py
"""

import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

# Import YAML parser
try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)

# Import the loader module
try:
    from alttprbot.tournament import registry_loader
except ImportError as e:
    print(f"ERROR: Failed to import registry_loader: {e}")
    sys.exit(1)


def validate_config():
    """Validate tournament configuration."""
    
    print("=" * 70)
    print("Tournament Registry Configuration Validator")
    print("=" * 70)
    print()
    
    # Define mock handlers for validation
    # In real use, these come from the actual tournament handler imports
    mock_handlers = {
        'test': object,
        'alttpr': object,
        'alttprdaily': object,
        'smz3': object,
        'invleague': object,
        'alttprleague': object,
        'boots': object,
        'nologic': object,
        'smwde': object,
        'alttprhmg': object,
        'alttprmini': object,
        'alttprde': object,
        'smrl': object,
    }
    
    config_path = repo_root / 'config' / 'tournaments.yaml'
    
    print(f"Validating config: {config_path}")
    print()
    
    # Step 1: Check file exists
    if not config_path.exists():
        print(f"✗ FAIL: Config file not found: {config_path}")
        return False
    
    print(f"✓ Config file exists")
    
    # Step 2: Load and validate YAML syntax
    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)
        print(f"✓ YAML syntax valid")
    except yaml.YAMLError as e:
        print(f"✗ FAIL: Invalid YAML syntax: {e}")
        return False
    except Exception as e:
        print(f"✗ FAIL: Error reading file: {e}")
        return False
    
    # Step 3: Validate schema
    try:
        registry_loader.validate_schema(data)
        print(f"✓ Schema validation passed")
    except registry_loader.TournamentConfigError as e:
        print(f"✗ FAIL: Schema validation failed: {e}")
        return False
    
    # Step 4: Validate handler references
    try:
        registry_loader.validate_handler_references(data, mock_handlers)
        print(f"✓ Handler reference validation passed")
    except registry_loader.TournamentConfigError as e:
        print(f"✗ FAIL: Handler reference validation failed: {e}")
        return False
    
    # Step 5: Load full config
    try:
        registry = registry_loader.load_tournament_config(
            available_handlers=mock_handlers,
            config_path=config_path
        )
        print(f"✓ Config loaded successfully")
    except registry_loader.TournamentConfigError as e:
        print(f"✗ FAIL: Failed to load config: {e}")
        return False
    
    # Step 6: Validate profiles
    print()
    print("Profile Summary:")
    print("-" * 70)
    
    for profile_name in ['debug', 'production']:
        profile = registry.get_profile(profile_name)
        if profile is None:
            print(f"✗ FAIL: Profile '{profile_name}' not found")
            return False
        
        enabled = profile.get_enabled_events()
        disabled = profile.get_disabled_events()
        
        print(f"\n{profile_name.upper()} Profile:")
        print(f"  Enabled events ({len(enabled)}):")
        for event in enabled:
            print(f"    - {event.event_slug} → {event.handler}")
        
        print(f"  Disabled events ({len(disabled)}):")
        for event in disabled:
            print(f"    - {event.event_slug} → {event.handler}")
    
    # Step 7: Test building active registries
    print()
    print("-" * 70)
    
    for profile_name in ['debug', 'production']:
        try:
            active_registry = registry_loader.build_active_registry(
                registry=registry,
                available_handlers=mock_handlers,
                profile_name=profile_name
            )
            print(f"✓ Active registry built for {profile_name} profile: {len(active_registry)} events")
        except Exception as e:
            print(f"✗ FAIL: Failed to build {profile_name} registry: {e}")
            return False
    
    print()
    print("=" * 70)
    print("✓ ALL VALIDATION CHECKS PASSED")
    print("=" * 70)
    
    return True


if __name__ == '__main__':
    success = validate_config()
    sys.exit(0 if success else 1)
