"""Discord presentation for the decomposed tournament system.

Holds the ``TournamentPresenter``: it turns the orchestrator's presentation-neutral
results (``SeedResult``) into Discord embeds and performs the Discord sends
(audit / commentary / player DMs / room info), resolving the ``TournamentDefinition``
IDs to live objects through the discord gateway. The service-tier orchestrator never
touches Discord directly — it hands neutral data to this presenter.
"""

from alttprbot.presentation.discord.tournament.presenter import TournamentPresenter

__all__ = ["TournamentPresenter"]
