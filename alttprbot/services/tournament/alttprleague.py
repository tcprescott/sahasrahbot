"""``ALTTPRLeagueOrchestrator`` — the ALTTPR League tournaments, decomposed.

Mirrors the legacy ``alttprleague.ALTTPRLeague`` / ``ALTTPROpenLeague``: an ALTTPR-family
seed-roll event whose preset is supplied per-episode by the external
``alttprleague.com/api/episode`` "mode" payload, with a spoiler-race branch, a dynamic
room goal / co-op / even-teams setup, and no room-welcome message.

The two legacy classes differed only in ``event_slug`` (their guild/channel/role config is
identical), so both are driven by this one orchestrator parameterised by a
``TournamentDefinition`` (``INVITATIONAL_LEAGUE_DEFINITION`` / ``OPEN_LEAGUE_DEFINITION``).

League-specific overrides vs the shared ALTTPR seed-roll lifecycle:
- ``update_data`` also fetches the league ``mode`` (preset + spoiler/co-op flags).
- ``room_creation_kwargs`` derives the goal/``team_race``/``require_even_teams`` from that mode.
- ``roll`` rolls the league preset, or a spoiler game (scheduling the spoiler race) when the
  mode is a spoiler.
- ``send_room_welcome`` is a no-op (legacy league suppressed the welcome + pinned action).
"""

from __future__ import annotations

import logging

import aiohttp

from alttprbot.services.seedgen import generator, spoilers
from alttprbot.services.tournament.alttpr import ALTTPRTournamentOrchestrator
from alttprbot.services.tournament.definition import TournamentDefinition
from alttprbot.services.tournament.types import SeedResult

LEAGUE_API_URL = "https://alttprleague.com/api/episode"

# Both league events share this guild / channel / role config (the legacy ALTTPROpenLeague
# extended ALTTPRLeague and overrode only the event_slug).
_LEAGUE_GUILD_ID = 543577975032119296
_LEAGUE_AUDIT_CHANNEL_ID = 546728638272241674
_LEAGUE_COMMENTARY_CHANNEL_ID = 1157407211094556703
_LEAGUE_HELPER_ROLE_IDS = [
    543596853871116288,
    543597099649073162,
    676530377812082706,
    553295025190993930,
    674109759179194398,
]


def _league_definition(event_slug: str) -> TournamentDefinition:
    return TournamentDefinition(
        event_slug=event_slug,
        racetime_category="alttpr",
        racetime_goal="Beat the game - Tournament (Solo)",
        guild_id=_LEAGUE_GUILD_ID,
        audit_channel_id=_LEAGUE_AUDIT_CHANNEL_ID,
        commentary_channel_id=_LEAGUE_COMMENTARY_CHANNEL_ID,
        helper_role_ids=list(_LEAGUE_HELPER_ROLE_IDS),
        stream_delay=10,
        create_scheduled_events=True,
    )


INVITATIONAL_LEAGUE_DEFINITION = _league_definition("invleague")
OPEN_LEAGUE_DEFINITION = _league_definition("alttprleague")


class ALTTPRLeagueOrchestrator(ALTTPRTournamentOrchestrator):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.league_data: dict = None

    # --- data loading: base episode/game/players + the external league mode ---
    async def update_data(self, *, update_episode: bool = True) -> None:
        await super().update_data(update_episode=update_episode)
        await self._get_league_data()

    async def _get_league_data(self) -> None:
        async with aiohttp.request("get", LEAGUE_API_URL, params={"id": self.episodeid}) as req:
            league_response = await req.json()

        try:
            self.league_data = league_response["mode"]
        except KeyError:
            logging.exception("No active league mode!")
            await self.racetime.send_message(
                self.room.name,
                "No active League mode!  This should not have happened.  Contact a league admin/mod for help.",
            )

    # --- room creation: dynamic goal / co-op / even-teams from the league mode ---
    @property
    def room_creation_kwargs(self) -> dict:
        if self.league_data["spoiler"]:
            goal_type = "Spoiler"
        elif self.league_data["coop"]:
            goal_type = "Tournament (Co-op)"
        else:
            goal_type = "Tournament (Solo)"

        kwargs = dict(super().room_creation_kwargs)
        kwargs["goal"] = f"Beat the game - {goal_type}"
        kwargs["team_race"] = self.league_data["coop"]
        kwargs["require_even_teams"] = True
        return kwargs

    # --- seed roll: league preset, or a scheduled spoiler game ---
    async def roll(self) -> SeedResult:
        if self.league_data.get("spoiler", False):
            spoiler = await spoilers.generate_spoiler_game(self.league_data["preset"])
            await self.racetime.schedule_spoiler_race(
                self.room.name, spoiler_url=spoiler.spoiler_log_url, studytime=0
            )
            return SeedResult(seed=spoiler.seed)

        seed = await generator.ALTTPRPreset(self.league_data["preset"]).generate(
            allow_quickswap=True, tournament=True, hints=False, spoilers="off"
        )
        return SeedResult(seed=seed)

    async def send_room_welcome(self) -> None:
        # League rooms intentionally have no welcome / pinned action (legacy override = pass).
        pass
