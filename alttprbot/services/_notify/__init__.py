"""Fire-and-forget notification plumbing for the service tier.

Services must not import the live Discord/RaceTime bot singletons, yet they need
to dispatch messages to those surfaces. This package provides:

- ``queue`` — an async work queue drained by a single worker, so dispatching a
  Discord DM or RaceTime chat message never blocks a DB transaction or request.
- ``discord_gateway`` / ``racetime_gateway`` — abstractions (protocol + registry)
  whose concrete implementations are registered *inward* by the presentation
  layer at startup. Services depend only on these abstractions.

Typical use from a service::

    from alttprbot.services._notify import discord_gateway, queue
    queue.enqueue(discord_gateway.get().send_dm(user_id, embed=payload))
"""

from alttprbot.services._notify import discord_gateway, queue, racetime_gateway

__all__ = ["discord_gateway", "queue", "racetime_gateway"]
