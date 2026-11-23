"""Service layer: domain operations that cogs, routes and racetime handlers call.

One module per domain. Services may use the Tortoise models directly, and must not
import ``alttprbot_discord``, ``alttprbot_racetime``, ``alttprbot_api`` or
``alttprbot_audit``.
"""
