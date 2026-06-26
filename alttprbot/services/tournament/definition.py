"""``TournamentDefinition`` — the discord-free config value object for an event.

The legacy ``TournamentConfig`` (``alttprbot/tournament/core.py``) holds live
``discord.Guild`` / ``discord.TextChannel`` / role objects resolved inside each
subclass's hardcoded ``configuration()`` method. ``TournamentDefinition`` is the
ID-only mirror: it carries the same configuration as plain ints/strings so the
orchestrator stays UI-free. The Discord presenter resolves the IDs to live objects
through the discord gateway when it actually needs to render or send.

Loaded per-event by ``registry_loader`` from ``config/tournaments.yaml`` (the
hardcoded IDs in each ``configuration()`` move here during the decomposition).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TournamentDefinition:
    # --- identity / racetime ---
    event_slug: str
    racetime_category: str
    racetime_goal: str

    schedule_type: str = "sg"
    lang: str = "en"
    coop: bool = False

    # --- discord ids (replace the resolved objects on TournamentConfig) ---
    guild_id: Optional[int] = None
    audit_channel_id: Optional[int] = None
    commentary_channel_id: Optional[int] = None
    mod_channel_id: Optional[int] = None
    scheduling_needs_channel_id: Optional[int] = None
    announce_channel_id: Optional[int] = None

    admin_role_ids: List[int] = field(default_factory=list)
    helper_role_ids: List[int] = field(default_factory=list)
    commentator_role_ids: List[int] = field(default_factory=list)
    mod_role_ids: List[int] = field(default_factory=list)
    announce_role_id: Optional[int] = None
    admin_user_ids: List[int] = field(default_factory=list)

    webhook_urls: Dict[str, str] = field(default_factory=dict)

    # --- scheduling / room behavior ---
    submission_form: Optional[str] = None
    create_scheduled_events: bool = False
    scheduling_needs_tracker: bool = False
    stream_delay: int = 0
    room_open_time: int = 35
    auto_record: bool = False
