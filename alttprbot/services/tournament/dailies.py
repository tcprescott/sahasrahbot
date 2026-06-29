"""SpeedGaming daily/weekly race orchestrators, decomposed.

Mirrors the legacy ``dailies`` package (``SGDailyRaceCore`` + ``AlttprSGDailyRace`` /
``SMZ3DailyRace``). These are **open casual races**, not tournament matches: the room is not
invitational, no players are invited or DMed, and ``!tournamentrace`` rolls nothing. Instead
of a per-player room-info DM the bot posts a public announcement to a channel (and, for the
ALTTPR daily, an SG webhook).

They therefore extend the **base** :class:`TournamentOrchestrator` and override:
- ``room_creation_kwargs`` — ``invitational=False`` and ``team_race`` from a "co-op" title match.
- ``update_data`` — fetch episode/game/restream team but resolve **no** players (open race).
- ``race_info`` / ``seed_time`` — the daily race-info string.
- ``send_player_room_info`` — post the channel/webhook announcement instead of DMing players.

Per-event differences (series label, whether the announcement includes the seed-distribution
time, the role-mention prefix, the webhook) are class attributes on the two concrete events.
"""

from __future__ import annotations

import datetime

import config
from alttprbot.repositories import TournamentGamesRepository
from alttprbot.services.tournament.core import TournamentOrchestrator
from alttprbot.services.tournament.definition import TournamentDefinition
from alttprbot.util import speedgaming

ALTTPR_DAILY_DEFINITION = TournamentDefinition(
    event_slug="alttprdaily",
    racetime_category="alttpr",
    racetime_goal="Beat the game - Casual",
    guild_id=307860211333595146,
    announce_channel_id=307861467838021633,
    room_open_time=60,
)

SMZ3_DAILY_DEFINITION = TournamentDefinition(
    event_slug="smz3",
    racetime_category="smz3",
    racetime_goal="Beat the games",
    guild_id=445948207638511616,
    announce_channel_id=451977523123978260,
    room_open_time=60,
)


class SGDailyOrchestrator(TournamentOrchestrator):
    """Shared base for the open SG daily/weekly races."""

    # --- per-event presentation config (overridden by the concrete events) ---
    series_label: str = ""
    include_seed_time: bool = False     # announce + race_info include the seed-distribution time
    announce_prefix: str = ""           # role-mention prefix on the announcement (smz3)
    webhook_url = None                  # an SG webhook to also post the announcement to (alttprdaily)
    webhook_role_mention = None

    @property
    def seed_time(self):
        return self.race_start_time - datetime.timedelta(minutes=10)

    @property
    def race_info(self) -> str:
        msg = f"{self.series_label} - {self.friendly_name} at {self.string_time(self.race_start_time)} Eastern"
        if self.broadcast_channels:
            msg += f" on {', '.join(self.broadcast_channels)}"
        if self.include_seed_time:
            msg += f" - Seed Distributed at {self.string_time(self.seed_time)} Eastern"
        msg += f" - {self.episodeid}"
        return msg

    @property
    def room_creation_kwargs(self) -> dict:
        kwargs = dict(super().room_creation_kwargs)
        kwargs["invitational"] = False
        kwargs["team_race"] = "co-op" in self.friendly_name.lower()
        return kwargs

    async def update_data(self, *, update_episode: bool = True) -> None:
        # Legacy SGDailyRaceCore.update_data always fetches the episode (it ignored
        # update_episode) and resolves NO players (open race — nobody is invited or DMed).
        self.episode = await speedgaming.get_episode(self.episodeid)
        self.tournament_game = await TournamentGamesRepository.get_by_episode_id(self.episodeid)
        self.restream_team = await self.racetime.get_team(self.definition.racetime_category, "sg-volunteers")

    async def send_player_room_info(self) -> None:
        await self.presenter.send_race_announcement(
            self.definition.announce_channel_id,
            prefix=self.announce_prefix,
            series=self.series_label,
            title=self.friendly_name,
            race_start_time=self.race_start_time,
            broadcast_channels=self.broadcast_channels,
            room_url=self.room.url,
            seed_time=self.seed_time if self.include_seed_time else None,
            webhook_url=self.webhook_url,
            webhook_role_mention=self.webhook_role_mention,
        )


class AlttprSGDailyOrchestrator(SGDailyOrchestrator):
    series_label = "SpeedGaming Daily Race Series"
    include_seed_time = True
    webhook_url = config.SG_DISCORD_WEBHOOK
    webhook_role_mention = "<@&399038388964950016>"


class SMZ3DailyOrchestrator(SGDailyOrchestrator):
    series_label = "SMZ3 Weekly Race"
    include_seed_time = False
    announce_prefix = "<@&449260882501959700> "
