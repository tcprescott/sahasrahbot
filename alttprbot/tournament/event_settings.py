"""Per-event tournament settings, read from ``tournaments.yaml`` at the repo root.

Each tournament or daily race class names its event slug, and
``tournament_config(slug)`` builds the ``TournamentConfig`` the race engine
uses: plain values are copied, and the Discord guild, channel and role ids are
resolved with the live bot (``alttprbot.services.bots``). ``announcement(slug)``
returns the room-opened announcement settings of a daily, as plain data.

The file is read once, when this module is imported (at startup), so nothing
blocks the event loop later.
"""

import dataclasses
from pathlib import Path

import yaml

from alttprbot.services import bots
from alttprbot.tournament.core import TournamentConfig

SETTINGS_FILE = Path(__file__).resolve().parents[2] / "tournaments.yaml"

CHANNEL_FIELDS = {
    'audit': 'audit_channel',
    'commentary': 'commentary_channel',
    'mod': 'mod_channel',
    'scheduling_needs': 'scheduling_needs_channel',
}
ROLE_FIELDS = {
    'admin': 'admin_roles',
    'helper': 'helper_roles',
    'commentator': 'commentator_roles',
    'mod': 'mod_roles',
}
# Keys of an entry that are not TournamentConfig fields.
STRUCTURED_KEYS = {'guild', 'channels', 'roles', 'announcement'}
CONFIG_FIELDS = {f.name for f in dataclasses.fields(TournamentConfig)}


class TournamentSettingsError(ValueError):
    """``tournaments.yaml`` is missing an event or holds a key the engine doesn't know."""


def load(path: Path = SETTINGS_FILE) -> dict:
    """Parse and validate a settings file. Returns ``{event_slug: entry}``."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    for slug, entry in data.items():
        _validate(slug, entry)
    return data


def _validate(slug: str, entry: dict):
    for required in ('guild', 'racetime_category', 'racetime_goal'):
        if required not in entry:
            raise TournamentSettingsError(f"tournaments.yaml: {slug} has no {required}")
    # event_slug is the entry's key, so it can't also be set inside it.
    unknown = (set(entry) - STRUCTURED_KEYS - CONFIG_FIELDS) | ({'event_slug'} & set(entry))
    if unknown:
        raise TournamentSettingsError(f"tournaments.yaml: {slug} has unknown keys {sorted(unknown)}")
    for name in entry.get('channels') or {}:
        if name not in CHANNEL_FIELDS:
            raise TournamentSettingsError(f"tournaments.yaml: {slug} has unknown channel {name!r}")
    for name in entry.get('roles') or {}:
        if name not in ROLE_FIELDS:
            raise TournamentSettingsError(f"tournaments.yaml: {slug} has unknown role list {name!r}")


SETTINGS = load()


def event(slug: str) -> dict:
    try:
        return SETTINGS[slug]
    except KeyError:
        raise TournamentSettingsError(f"tournaments.yaml has no entry for {slug!r}") from None


def tournament_config(slug: str, **overrides) -> TournamentConfig:
    """The ``TournamentConfig`` for an event, with its Discord objects resolved."""
    entry = event(slug)
    client = bots.discord()
    guild = client.get_guild(entry['guild'])

    kwargs = {k: v for k, v in entry.items() if k not in STRUCTURED_KEYS}
    kwargs['event_slug'] = slug
    for name, channel_id in (entry.get('channels') or {}).items():
        kwargs[CHANNEL_FIELDS[name]] = client.get_channel(channel_id)
    for name, role_ids in (entry.get('roles') or {}).items():
        kwargs[ROLE_FIELDS[name]] = [guild.get_role(role_id) for role_id in role_ids]
    kwargs.update(overrides)
    return TournamentConfig(guild=guild, **kwargs)


def announcement(slug: str):
    """The room-opened announcement settings for a daily, or None."""
    entry = SETTINGS.get(slug)
    return entry.get('announcement') if entry else None
