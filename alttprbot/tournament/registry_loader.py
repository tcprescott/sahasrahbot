"""
Tournament Registry Loader

Loads and validates tournament configuration from YAML.
Part of Phase 0/1 of tournament registry config rollout.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml


class TournamentConfigError(Exception):
    """Raised when tournament configuration is invalid."""
    pass


class EventConfig:
    """Represents a single event configuration."""
    
    def __init__(self, event_slug: str, handler: str, enabled: bool, notes: Optional[str] = None):
        self.event_slug = event_slug
        self.handler = handler
        self.enabled = enabled
        self.notes = notes
    
    def __repr__(self):
        return f"EventConfig(event_slug={self.event_slug!r}, handler={self.handler!r}, enabled={self.enabled})"


class ProfileConfig:
    """Represents a profile configuration (debug or production)."""
    
    def __init__(self, events: List[EventConfig]):
        self.events = events
    
    def get_enabled_events(self) -> List[EventConfig]:
        """Return only enabled events."""
        return [e for e in self.events if e.enabled]
    
    def get_disabled_events(self) -> List[EventConfig]:
        """Return only disabled events."""
        return [e for e in self.events if not e.enabled]


class TournamentRegistry:
    """Loaded and validated tournament configuration."""
    
    def __init__(self, version: int, profiles: Dict[str, ProfileConfig]):
        self.version = version
        self.profiles = profiles
    
    def get_profile(self, profile_name: str) -> Optional[ProfileConfig]:
        """Get a specific profile by name."""
        return self.profiles.get(profile_name)


def load_yaml_config(config_path: Path) -> Dict[str, Any]:
    """
    Load and parse YAML configuration file.
    
    Args:
        config_path: Path to the YAML config file
        
    Returns:
        Parsed YAML data as dict
        
    Raises:
        TournamentConfigError: If file cannot be read or parsed
    """
    try:
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        if data is None:
            raise TournamentConfigError(f"Config file is empty: {config_path}")
        
        return data
    
    except FileNotFoundError:
        raise TournamentConfigError(f"Config file not found: {config_path}")
    except yaml.YAMLError as e:
        raise TournamentConfigError(f"YAML parse error: {e}")
    except Exception as e:
        raise TournamentConfigError(f"Error reading config file: {e}")


def validate_schema(data: Dict[str, Any]) -> None:
    """
    Validate the schema of the configuration data.
    
    Args:
        data: Parsed YAML data
        
    Raises:
        TournamentConfigError: If schema validation fails
    """
    # Check top-level keys
    if 'version' not in data:
        raise TournamentConfigError("Missing required key: 'version'")
    
    if 'profiles' not in data:
        raise TournamentConfigError("Missing required key: 'profiles'")
    
    # Validate version
    if not isinstance(data['version'], int):
        raise TournamentConfigError("'version' must be an integer")
    
    if data['version'] != 1:
        raise TournamentConfigError(f"Unsupported config version: {data['version']} (expected 1)")
    
    # Validate profiles
    profiles = data['profiles']
    if not isinstance(profiles, dict):
        raise TournamentConfigError("'profiles' must be a dictionary")
    
    # Check required profiles
    required_profiles = ['debug', 'production']
    for profile_name in required_profiles:
        if profile_name not in profiles:
            raise TournamentConfigError(f"Missing required profile: '{profile_name}'")
    
    # Validate each profile
    for profile_name, profile_data in profiles.items():
        if not isinstance(profile_data, dict):
            raise TournamentConfigError(f"Profile '{profile_name}' must be a dictionary")
        
        if 'events' not in profile_data:
            raise TournamentConfigError(f"Profile '{profile_name}' missing required key: 'events'")
        
        events = profile_data['events']
        if not isinstance(events, list):
            raise TournamentConfigError(f"Profile '{profile_name}': 'events' must be a list")
        
        # Validate each event
        event_slugs_seen = set()
        for idx, event in enumerate(events):
            if not isinstance(event, dict):
                raise TournamentConfigError(
                    f"Profile '{profile_name}': event at index {idx} must be a dictionary"
                )
            
            # Check required fields
            required_event_fields = ['event_slug', 'handler', 'enabled']
            for field in required_event_fields:
                if field not in event:
                    raise TournamentConfigError(
                        f"Profile '{profile_name}': event at index {idx} missing required field: '{field}'"
                    )
            
            # Validate field types
            event_slug = event['event_slug']
            handler = event['handler']
            enabled = event['enabled']
            
            if not isinstance(event_slug, str) or not event_slug:
                raise TournamentConfigError(
                    f"Profile '{profile_name}': event at index {idx}: 'event_slug' must be a non-empty string"
                )
            
            if not isinstance(handler, str) or not handler:
                raise TournamentConfigError(
                    f"Profile '{profile_name}': event at index {idx}: 'handler' must be a non-empty string"
                )
            
            if not isinstance(enabled, bool):
                raise TournamentConfigError(
                    f"Profile '{profile_name}': event at index {idx}: 'enabled' must be a boolean"
                )
            
            # Check for duplicate event_slug
            if event_slug in event_slugs_seen:
                raise TournamentConfigError(
                    f"Profile '{profile_name}': duplicate event_slug: '{event_slug}'"
                )
            event_slugs_seen.add(event_slug)
            
            # Validate notes if present
            if 'notes' in event:
                notes = event['notes']
                if notes is not None and not isinstance(notes, str):
                    raise TournamentConfigError(
                        f"Profile '{profile_name}': event '{event_slug}': 'notes' must be a string or null"
                    )


def validate_handler_references(data: Dict[str, Any], available_handlers: Dict[str, Any]) -> None:
    """
    Validate that all handler references exist in AVAILABLE_TOURNAMENT_HANDLERS.
    
    Args:
        data: Parsed YAML data
        available_handlers: Dictionary of available tournament handlers
        
    Raises:
        TournamentConfigError: If any handler reference is invalid
    """
    profiles = data['profiles']
    
    for profile_name, profile_data in profiles.items():
        events = profile_data['events']
        
        for event in events:
            handler = event['handler']
            event_slug = event['event_slug']
            
            if handler not in available_handlers:
                raise TournamentConfigError(
                    f"Profile '{profile_name}': event '{event_slug}': "
                    f"unknown handler '{handler}'. "
                    f"Available handlers: {', '.join(sorted(available_handlers.keys()))}"
                )


def parse_config(data: Dict[str, Any]) -> TournamentRegistry:
    """
    Parse validated YAML data into TournamentRegistry object.
    
    Args:
        data: Validated YAML data
        
    Returns:
        TournamentRegistry instance
    """
    version = data['version']
    profiles_data = data['profiles']
    
    profiles = {}
    for profile_name, profile_data in profiles_data.items():
        events = []
        for event_data in profile_data['events']:
            event = EventConfig(
                event_slug=event_data['event_slug'],
                handler=event_data['handler'],
                enabled=event_data['enabled'],
                notes=event_data.get('notes')
            )
            events.append(event)
        
        profiles[profile_name] = ProfileConfig(events)
    
    return TournamentRegistry(version=version, profiles=profiles)


def load_tournament_config(
    available_handlers: Dict[str, Any],
    config_path: Optional[Path] = None
) -> TournamentRegistry:
    """
    Load and validate tournament configuration from YAML.
    
    Args:
        available_handlers: Dictionary of available tournament handlers
        config_path: Path to config file (defaults to config/tournaments.yaml)
        
    Returns:
        TournamentRegistry instance with validated configuration
        
    Raises:
        TournamentConfigError: If configuration is invalid or cannot be loaded
    """
    # Default config path
    if config_path is None:
        # Assume we're running from repo root
        repo_root = Path(__file__).parent.parent.parent
        config_path = repo_root / 'config' / 'tournaments.yaml'
    
    # Load YAML
    data = load_yaml_config(config_path)
    
    # Validate schema
    validate_schema(data)
    
    # Validate handler references
    validate_handler_references(data, available_handlers)
    
    # Parse into objects
    registry = parse_config(data)
    
    return registry


def build_active_registry(
    registry: TournamentRegistry,
    available_handlers: Dict[str, Any],
    profile_name: str
) -> Dict[str, Any]:
    """
    Build active tournament registry from configuration.
    
    Args:
        registry: Loaded TournamentRegistry
        available_handlers: Dictionary of available tournament handlers
        profile_name: Profile to use ('debug' or 'production')
        
    Returns:
        Dictionary mapping event slug to handler class (only enabled events)
        
    Raises:
        TournamentConfigError: If profile not found
    """
    profile = registry.get_profile(profile_name)
    if profile is None:
        raise TournamentConfigError(f"Profile not found: '{profile_name}'")
    
    active_registry = {}
    enabled_events = profile.get_enabled_events()
    
    for event in enabled_events:
        handler_class = available_handlers[event.handler]
        active_registry[event.event_slug] = handler_class
    
    return active_registry


def log_registry_summary(
    registry: TournamentRegistry,
    profile_name: str,
    active_registry: Dict[str, Any]
) -> None:
    """
    Log summary of loaded registry configuration.
    
    Args:
        registry: Loaded TournamentRegistry
        profile_name: Active profile name
        active_registry: Built active registry
    """
    profile = registry.get_profile(profile_name)
    if profile is None:
        return
    
    enabled_events = profile.get_enabled_events()
    disabled_events = profile.get_disabled_events()
    
    enabled_slugs = [e.event_slug for e in enabled_events]
    
    logging.info(
        f"Tournament Registry: source=config, profile={profile_name}, "
        f"enabled_events_count={len(enabled_events)}, "
        f"disabled_events_count={len(disabled_events)}, "
        f"enabled_event_slugs={enabled_slugs}"
    )
