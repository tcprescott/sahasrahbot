"""Presentation tier (Tier 1).

Thin adapters for each surface — Discord (main + audit), RaceTime.gg, and the
Quart web API. Presentation code parses input, calls the service tier, renders
results, and catches service errors. It must not contain business logic and must
not import ``alttprbot.repositories`` or ``alttprbot.models`` directly.

The four surfaces are folded in here during the Great Relocation phase:
``discord/``, ``audit/``, ``racetime/``, ``api/``.
"""
