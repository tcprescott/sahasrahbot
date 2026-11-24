"""Observability: Sentry errors, logs, traces, profiles and metrics.

* :mod:`.sentry`: ``init_sentry`` and the settings, hooks and scope helpers.
* :mod:`.metrics`: no-op-safe ``gauge`` / ``count`` / ``distribution`` wrappers.
* :mod:`.instrument`: times every service, API-client and seed-generator call.
* :mod:`.runtime`: process, event-loop, GC, DB-pool and bot gauges every 30s.
* :mod:`.watchdog`: names the code that blocks the event loop.

Core code; imports no front end. The front ends add their own pieces:
``alttprbot_api/telemetry.py``, ``alttprbot_discord/telemetry.py`` and the race
handler in ``alttprbot_racetime/handlers/core.py``. What each signal is, and how
to use it during an incident, is in CLAUDE.md under "Sentry".
"""
