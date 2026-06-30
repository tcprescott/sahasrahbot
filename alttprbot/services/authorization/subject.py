"""The normalized, surface-agnostic authorization subject (the XACML *principal*).

Each presentation surface builds an :class:`AuthSubject` fresh per request/command
from its own platform objects (a discord ``Interaction``/``Member``, a quart
``session``, a racetime handler ``message``) and passes it to
``AuthorizationService``. The service decides against this plain data and never
touches a ``discord``/``racetime_bot``/``quart`` object, satisfying the
import-linter boundary (services may not import UI/transport libraries).

Build it fresh every call — never cache it or derive it from a stale token — so
authorization always decides against current facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import FrozenSet, Optional

from alttprbot import models


@dataclass(frozen=True)
class AuthSubject:
    # --- discord identity ---
    discord_user_id: Optional[int] = None
    discord_role_ids: FrozenSet[int] = frozenset()      # {r.id for r in member.roles}
    guild_id: Optional[int] = None
    account_created_at: Optional[datetime] = None        # async account-age (ABAC) gate

    # --- linked / racetime identity ---
    user: Optional[models.Users] = None                  # resolved Users row (rtgg_id, discord link)
    rtgg_id: Optional[str] = None
    is_race_monitor: bool = False                        # racetime can_monitor(message)
    race_entrant_ids: FrozenSet[str] = frozenset()       # rtgg ids of current entrants

    # --- capability ---
    api_key: Optional[str] = None
