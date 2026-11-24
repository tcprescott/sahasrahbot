"""Clients for the external HTTP APIs SahasrahBot calls.

One module per service. Each one only talks HTTP and returns plain data
(dicts, lists, ints): no Discord, racetime-bot or web imports, no models and no
business rules. Those belong to the callers, usually a service in
``alttprbot/services/``.

The seed generators' clients live with them in ``alttprbot/alttprgen/randomizer/``.
"""
