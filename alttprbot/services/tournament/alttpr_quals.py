"""``ALTTPRQualifierOrchestrator`` — the ALTTPR main-tournament live qualifier, decomposed.

Mirrors the legacy ``alttpr_quals.ALTTPRQualifierRace`` — the most entangled handler: it
bridges the live-race system with the AsyncTournament system. It is an open race (announced
to a channel, no player invites/DMs) but with a heavy ``!tournamentrace`` flow:

- ``before_room_creation`` — only open a room if a live race is configured for the episode.
- ``process_race`` — guard conditions, a mod/admin authz check, lock the room, roll the seed
  (``triforce_text``), persist the permalink, and write an ``AsyncTournamentRace`` row for each
  eligible entrant.
- ``on_race_start`` — flip pending entrants to in-progress, prune no-shows, announce the field.

All Discord/RaceTime I/O goes through the presenter / racetime gateway; the AsyncTournament
ORM goes through repositories; the mod/admin authz check (which needs ``discordbot``) is an
adapter-supplied callback.
"""

from __future__ import annotations

import datetime

import isodate
import pytz

from alttprbot.repositories import (
    AsyncTournamentLiveRaceRepository,
    AsyncTournamentRepository,
    TournamentGamesRepository,
    TournamentResultsRepository,
    UserRepository,
)
from alttprbot.services.tournament.core import TournamentOrchestrator
from alttprbot.services.tournament.definition import TournamentDefinition
from alttprbot.util import speedgaming, triforce_text

QUALIFIER_DEFINITION = TournamentDefinition(
    event_slug="alttpr",
    racetime_category="alttpr",
    racetime_goal="Beat the game - Tournament (Solo)",
    guild_id=334795604918272012,
    audit_channel_id=647966639266201620,
    commentary_channel_id=947095820673638400,
    scheduling_needs_channel_id=434560353461075969,
    scheduling_needs_tracker=True,
    create_scheduled_events=True,
    announce_channel_id=407803705375850506,
    room_open_time=60,
    helper_role_ids=[
        334797023054397450,
        435200206552694794,
        482353483853332481,
        426487540829388805,
        613394561594687499,
        334796844750209024,
    ],
)


class ALTTPRQualifierOrchestrator(TournamentOrchestrator):
    # --- room creation: only when a live race is configured (legacy construct_race_room gate) ---
    async def before_update_data(self) -> bool:
        # Gate BEFORE any SpeedGaming/RaceTime I/O, matching the legacy construct_race_room
        # which looked up the live race first and returned None silently when absent.
        live_race = await AsyncTournamentLiveRaceRepository.get_by_episode_id(self.episodeid)
        return live_race is not None

    @property
    def room_creation_kwargs(self) -> dict:
        kwargs = dict(super().room_creation_kwargs)
        kwargs.update(
            invitational=False,
            start_delay=30,
            auto_start=False,
            allow_prerace_chat=False,
            allow_midrace_chat=False,
        )
        return kwargs

    async def update_data(self, *, update_episode: bool = True) -> None:
        if update_episode:
            self.episode = await speedgaming.get_episode(self.episodeid)
        self.tournament_game = await TournamentGamesRepository.get_by_episode_id(self.episodeid)
        self.restream_team = await self.racetime.get_team(self.definition.racetime_category, "sg-volunteers")
        # open race — no player resolution

    @property
    def seed_time(self):
        return self.race_start_time - datetime.timedelta(minutes=10)

    @property
    def race_info(self) -> str:
        msg = (
            f"ALTTPR Main Tournament Live Qualifier - {self.friendly_name} "
            f"at {self.string_time(self.race_start_time)} Eastern"
        )
        if self.broadcast_channels:
            msg += f" on {', '.join(self.broadcast_channels)}"
        msg += f" - Seed Distributed and Room Locked at {self.string_time(self.seed_time)} Eastern"
        msg += f" - {self.episodeid}"
        return msg

    async def send_player_room_info(self) -> None:
        await self.presenter.send_race_announcement(
            self.definition.announce_channel_id,
            prefix="",
            series="ALTTPR Main Tournament Live Qualifier",
            title=self.friendly_name,
            race_start_time=self.race_start_time,
            broadcast_channels=self.broadcast_channels,
            room_url=self.room.url,
            seed_time=self.seed_time,
            seed_label="Seed Distributed and Room Lock",
        )

    # --- the !tournamentrace seed roll ---
    async def process_race(self, args, message) -> bool:
        room = self.room.name
        await self.racetime.send_message(
            room, "Generating game, please wait.  If nothing happens after a minute, contact Synack."
        )
        await self.update_data()

        live_race = await AsyncTournamentLiveRaceRepository.get_by_episode_id_with_relations(self.episodeid)

        if live_race is None:
            await self.racetime.send_message(
                room, "No live race found for this episode.  Please contact Synack for further help."
            )
            return False
        if live_race.permalink is not None:
            await self.racetime.send_message(
                room,
                "Seed has already been generated for this live race.  Please contact Synack for further help.",
            )
            return False
        if live_race.pool is None:
            await self.racetime.send_message(
                room, "No pool has been set for this live race.  Please contact Synack for further help."
            )
            return False

        user = await UserRepository.get_by_rtgg_id(message["user"]["id"])
        authorized = await self._async_authz_checker(user, live_race.tournament, ["admin", "mod"])
        if not authorized:
            await self.racetime.send_message(
                room,
                "Only a mod or admin of this tournament may invoke !tournamentrace.  "
                "Please contact Synack for further help.",
            )
            return False

        if live_race.pool.preset is None:
            await self.racetime.send_message(
                room, "No preset has been set for this pool.  Please contact Synack for further help."
            )
            return False

        # lock the room
        await self.racetime.set_invitational(room)
        await self.racetime.send_message(room, "This room is now locked.  Late entries are not permitted.")

        seed = await triforce_text.generate_with_triforce_text("alttpr2024", live_race.pool.preset)
        seed_code = f"({'/'.join(seed.code)})"

        await self.racetime.set_bot_raceinfo(room, f"{seed.url} - {seed_code}")
        await self.racetime.send_message(room, f"Seed: {seed.url} - {seed_code}")
        await self.presenter.send_audit_message(f"{self.room.url} - {seed.url} - {seed_code}")

        await TournamentResultsRepository.create_or_update_with_permalink(
            srl_id=room,
            defaults={"episode_id": self.episodeid, "event": self.event_slug, "spoiler": None},
            permalink=seed.url,
        )

        permalink = await AsyncTournamentRepository.create_live_permalink(
            url=seed.url, pool=live_race.pool, notes=f"Generated for a live race.  {seed_code}"
        )
        await AsyncTournamentLiveRaceRepository.set_permalink_and_slug(live_race, permalink, room)

        eligible_entrants = await self._write_eligible_entrants(live_race, permalink)

        # NOTE: the adapter sets the handler's seed_rolled guard on this True return. Legacy
        # set it just before these last two messages; double-rolling is independently blocked by
        # the live_race.permalink guard above (now set), so the ordering is behavior-preserving.
        await self.presenter.send_audit_message(
            f"{self.room.url} -Eligible entrants for this pool: {', '.join(eligible_entrants)}"
        )
        await self.racetime.send_message(
            room, f"Eligible entrants for this pool: {', '.join(eligible_entrants)}"
        )
        return True

    async def _write_eligible_entrants(self, live_race, permalink) -> list:
        """Create an AsyncTournamentRace row per eligible entrant; return their display names.

        Mirrors the legacy ``write_eligible_async_entrants``: upsert each entrant's ``Users``
        row (refreshing twitch name), skip anyone who has hit the per-pool run limit or already
        has an active race, otherwise create a pending live-race entry.
        """
        tournament = live_race.tournament
        pool = live_race.pool
        entrants = await self.racetime.get_entrants(self.room.name)

        eligible = []
        for entrant in entrants:
            user, created = await UserRepository.get_or_create_by_rtgg_id(
                entrant["id"],
                defaults={"display_name": entrant["name"], "twitch_name": entrant["twitch_name"]},
            )
            if not created:
                await UserRepository.set_twitch_name(user, entrant["twitch_name"])

            if await AsyncTournamentRepository.count_completed_pool_races(tournament, user, pool) >= tournament.runs_per_pool:
                continue
            if await AsyncTournamentRepository.user_has_active_race(tournament, user):
                continue

            await AsyncTournamentRepository.create_pending_live_entry(tournament, permalink, user, live_race)
            eligible.append(user.display_name)

        return eligible

    # --- race start: promote actual entrants, prune no-shows, announce the field ---
    async def on_race_start(self) -> None:
        live_race = await AsyncTournamentLiveRaceRepository.get_by_episode_id(self.episodeid)
        entrant_ids = await self.racetime.get_entrant_ids(self.room.name)
        started_at = await self.racetime.get_started_at(self.room.name)
        start_time = isodate.parse_datetime(started_at).astimezone(pytz.utc)

        in_progress = await AsyncTournamentLiveRaceRepository.process_race_start(
            live_race, entrant_ids, start_time
        )

        await self.presenter.send_audit_message(f"{self.room.url} - Entrants: {', '.join(in_progress)}")
        await self.racetime.send_message(
            self.room.name, f"Final eligible entrants for this pool: {', '.join(in_progress)}"
        )
        await self.racetime.send_message(
            self.room.name,
            "Good luck, have fun!  Mid-race chat is disabled.  If you need assistance, "
            "please ping @Admins in Discord.",
        )
