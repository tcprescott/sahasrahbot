"""RaceTime presentation adapter for authorization.

Builds the surface-agnostic :class:`~alttprbot.services.AuthSubject` from a
racetime handler + command message (the Policy Information Point). The
racetime-library monitor concept (``can_monitor`` / ``@monitor_cmd``) stays native
in presentation; only the combined entrant-or-monitor seed-roll policy is decided
by ``AuthorizationService``.
"""

from racetime_bot import can_monitor

from alttprbot.services import AuthSubject

# Entrant statuses that count as "in the race" for seed-roll eligibility.
_ACTIVE_ENTRANT_STATUSES = ('ready', 'not_ready', 'in_progress', 'done', 'dnf', 'dq')


def subject_from_message(handler, message) -> AuthSubject:
    entrant_ids = frozenset(
        entrant['user']['id']
        for entrant in handler.data.get('entrants', [])
        if entrant['status']['value'] in _ACTIVE_ENTRANT_STATUSES
    )
    return AuthSubject(
        rtgg_id=message.get('user', {}).get('id', None),
        race_entrant_ids=entrant_ids,
        is_race_monitor=can_monitor(message),
    )
