"""``TournamentOrchestrator`` — the business core of the decomposed tournament system.

A behavior-preserving port of the lifecycle on the legacy ``TournamentRace``
god-object (``alttprbot/tournament/core.py``), with every Discord/RaceTime concern
pushed out:

- Discord rendering / sends  -> the injected ``TournamentPresenter``.
- RaceTime I/O                -> the injected ``racetime`` gateway.
- TournamentResults/Games ORM -> repositories.
- Discord member/role resolution (player lookup, gatekeeper role check) -> injected
  resolver callbacks supplied by the presentation adapter (which may touch Discord).

The orchestrator therefore imports no ``discord`` / ``racetime_bot`` / ``alttprbot.presentation``.
It works on the presentation-neutral ``TournamentDefinition`` (config IDs) and
``TournamentPlayer`` / ``RaceRoom`` value objects. Per-event subclasses override only
the business hooks (``roll`` / ``process_race`` / the ``on_*`` lifecycle hooks).
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, List, Optional

import dateutil.parser
import pytz

import config
from alttprbot.repositories import (
    TournamentGamesRepository,
    TournamentResultsRepository,
    UserRepository,
)
from alttprbot.services._notify import racetime_gateway
from alttprbot.services.tournament.definition import TournamentDefinition
from alttprbot.services.tournament.types import RaceRoom, TournamentPlayer
from alttprbot.util import speedgaming

APP_URL = config.APP_URL

# adapter-supplied callbacks (presentation does the Discord-specific resolution)
PlayerResolver = Callable[[dict], Awaitable[Optional[TournamentPlayer]]]
GatekeepChecker = Callable[[int, list], Awaitable[bool]]


class TournamentOrchestrator:
    def __init__(
        self,
        definition: TournamentDefinition,
        episodeid: int = None,
        *,
        presenter,
        player_resolver: PlayerResolver,
        gatekeep_checker: GatekeepChecker,
        racetime=None,
        async_authz_checker=None,
    ) -> None:
        try:
            self.episodeid = int(episodeid)
        except TypeError:
            self.episodeid = episodeid

        self.definition = definition
        self.presenter = presenter
        self._racetime = racetime
        self._player_resolver = player_resolver
        self._gatekeep_checker = gatekeep_checker
        # adapter-supplied async-tournament authz check (DB + discord guild role); only the
        # alttpr_quals orchestrator uses it (wired to the coordinator's _check_async_authz,
        # which delegates to AuthorizationService.is_async_tournament_user).
        self._async_authz_checker = async_authz_checker

        # runtime state
        self.episode: Optional[dict] = None
        self.tournament_game = None
        self.players: List[TournamentPlayer] = []
        self.restream_team = None
        self.room: Optional[RaceRoom] = None

    @property
    def racetime(self):
        return self._racetime if self._racetime is not None else racetime_gateway.get()

    # --- data loading (mirrors TournamentRace.update_data) ---
    async def update_data(self, *, update_episode: bool = True) -> None:
        if update_episode:
            self.episode = await speedgaming.get_episode(self.episodeid)

        self.tournament_game = await TournamentGamesRepository.get_by_episode_id(self.episodeid)
        self.restream_team = await self.racetime.get_team(self.definition.racetime_category, "sg-volunteers")

        self.players = []
        for player in self.episode["match1"]["players"]:
            if player["publicStream"] == "ignore":
                continue
            resolved = await self._player_resolver(player)
            self.players.append(resolved)

    # --- room lifecycle (room is created by the adapter, which holds the handler) ---
    @property
    def room_creation_kwargs(self) -> dict:
        """The ``startrace`` kwargs (mirrors TournamentRace.create_race_room)."""
        return dict(
            goal=self.definition.racetime_goal,
            invitational=True,
            unlisted=False,
            info_user=self.race_info,
            start_delay=15,
            time_limit=24,
            streaming_required=True,
            auto_start=True,
            allow_comments=True,
            hide_comments=True,
            allow_prerace_chat=True,
            allow_midrace_chat=True,
            allow_non_entrant_chat=False,
            chat_message_delay=0,
            team_race=self.definition.coop,
        )

    async def on_room_created(self, room: RaceRoom) -> None:
        """Mirror the tail of TournamentRace.construct_race_room once the room exists."""
        self.room = room
        await TournamentResultsRepository.upsert_by_srl_id(
            srl_id=room.name,
            defaults={"episode_id": self.episodeid, "event": self.event_slug, "spoiler": None},
        )
        for rtgg_id in self.player_racetime_ids:
            await self.racetime.invite_user(room.name, rtgg_id)

        await self.send_player_room_info()
        await self.send_room_welcome()
        await self.on_room_creation()

    async def send_player_room_info(self) -> None:
        await self.presenter.send_player_room_info(
            self.player_discord_ids, versus=self.versus, room_url=self.room.url
        )

    # --- gatekeeping (team check + Users lookup here; member-role check via callback) ---
    async def can_gatekeep(self, rtgg_id: str) -> bool:
        team_member_ids = [m["id"] for m in self.restream_team["members"]]
        if rtgg_id in team_member_ids:
            return True

        user = await UserRepository.get_by_rtgg_id(rtgg_id)
        if not user:
            return False

        return await self._gatekeep_checker(user.discord_user_id, self.definition.helper_role_ids)

    # --- room-creation gates (overridden per event; default allows creation) ---
    async def before_update_data(self) -> bool:
        """Pre-I/O room-creation gate, run *before* ``update_data``.

        The dispatch adapter calls this right after building the orchestrator, before any
        SpeedGaming / RaceTime I/O. Use it for cheap checks that should short-circuit room
        creation without doing that work (e.g. the alttpr_quals live-race lookup, which the
        legacy ``construct_race_room`` did first and returned ``None`` from silently). The
        default allows creation. Gates that need ``update_data`` to have run (e.g. the smrl
        submitted-settings check) belong in :meth:`before_room_creation` instead.
        """
        return True

    async def before_room_creation(self) -> bool:
        """Return ``False`` to abort room creation (handling the abort itself).

        The dispatch adapter calls this after ``update_data`` and before opening the
        RaceTime room. The default allows creation. Events that require submitted settings
        (e.g. ``smrl``) override this to send a submission reminder and return ``False``.

        Note this is an intentional *cleanup* of a latent legacy bug, not a faithful mirror:
        legacy ``create_race_room`` returned ``None`` in this case, which the un-null-checked
        base ``construct_race_room`` then dereferenced (``handler.tournament = ...``) — raising
        ``AttributeError`` and posting a spurious "error creating a race room" audit message.
        The clean early-return drops that crash + spurious message; the warning DMs and the
        ``submitted`` upsert are identical to before.
        """
        return True

    # --- business hooks (overridden per event; no-op base) ---
    async def roll(self):
        pass

    async def create_embeds(self):
        pass

    async def send_room_welcome(self):
        pass

    async def on_room_creation(self):
        pass

    async def on_room_resume(self):
        pass

    async def on_race_start(self):
        pass

    async def on_race_pending(self):
        pass

    async def process_race(self, args, message) -> bool:
        """Handle the ``!tournamentrace`` seed-roll for this room.

        Returns ``True`` when a seed was rolled (the dispatch adapter then sets the
        RaceTime handler's ``seed_rolled`` guard). The no-op base returns falsy, so a
        handler that does not roll (e.g. the debug ``test`` event) never trips the guard
        — matching the legacy base ``process_tournament_race`` which did nothing.
        """
        return False

    async def process_submission_form(self, payload, submitted_by):
        """Handle a settings-submission POST. No-op base (legacy ``process_submission_form``)."""
        pass

    # --- submission reminders (mirrors TournamentRace.send_race_submission_form) ---
    async def send_race_submission_form(self, warning: bool = False) -> None:
        if self.submission_form is None:
            return
        if self.tournament_game and self.tournament_game.submitted and not warning:
            return

        if warning:
            msg = (
                f"Your upcoming race room cannot be created because settings have not submitted: `{self.versus}`!\n\n"
                f"For your convenience, please visit {self.submit_link} to submit the settings.\n\n"
            )
        else:
            msg = (
                f"Greetings!  Do not forget to submit settings for your upcoming race: `{self.versus}`!\n\n"
                f"For your convenience, please visit {self.submit_link} to submit the settings.\n\n"
            )

        await self.presenter.send_player_reminders(self.player_discord_ids, msg)
        await TournamentGamesRepository.upsert_by_episode_id(
            episode_id=self.episodeid,
            defaults={"event": self.event_slug, "submitted": 1},
        )

    # --- pure, presentation-neutral properties (ported verbatim) ---
    @property
    def lang(self) -> str:
        return self.definition.lang

    @property
    def submission_form(self) -> Any:
        return self.definition.submission_form

    @property
    def submit_link(self) -> str:
        return f"{APP_URL}/submit/{self.event_slug}?episode_id={self.episodeid}"

    @property
    def game_number(self):
        if self.tournament_game:
            return self.tournament_game.game_number
        return ""

    @property
    def event_name(self) -> str:
        return self.episode["event"]["shortName"]

    @property
    def event_slug(self) -> str:
        return self.episode["event"]["slug"]

    @property
    def friendly_name(self) -> str:
        return self.episode["match1"]["title"]

    @property
    def versus(self) -> str:
        separator = " vs. "
        if len(self.player_names) > 2:
            separator = ", "
        return separator.join(self.player_names)

    @property
    def player_racetime_ids(self) -> list:
        return [p.rtgg_id for p in self.players]

    @property
    def player_discord_ids(self) -> list:
        return [p.discord_user_id for p in self.players]

    @property
    def player_names(self) -> list:
        return [p.name for p in self.players]

    @property
    def player_twitch_names(self) -> list:
        return [p["streamingFrom"] for p in self.episode["match1"]["players"]]

    @property
    def broadcast_channels(self) -> list:
        return [a["name"] for a in self.episode["channels"] if " " not in a["name"]]

    @property
    def broadcast_channel_links(self) -> str:
        return ", ".join([f"[{a}](https://twitch.tv/{a})" for a in self.broadcast_channels])

    @property
    def seed_code(self):
        return None

    @property
    def race_info(self) -> str:
        info = f"{self.event_name} - {self.versus} - {self.friendly_name}"
        if self.game_number:
            info += f" - Game #{self.game_number}"
        if self.broadcast_channels:
            info += f" - Restream(s) at {', '.join(self.broadcast_channels)}"
        info += f" - {self.episodeid}"
        return info

    @property
    def race_start_time(self):
        return dateutil.parser.parse(self.episode["whenCountdown"])

    @property
    def race_start_time_restream(self):
        return dateutil.parser.parse(self.episode["when"])

    def string_time(self, date) -> str:
        return date.astimezone(self.timezone).strftime("%-I:%M %p")

    @property
    def timezone(self):
        return pytz.timezone("US/Eastern")

    @property
    def hours_before_room_open(self):
        return (self.definition.stream_delay + self.definition.room_open_time) / 60
