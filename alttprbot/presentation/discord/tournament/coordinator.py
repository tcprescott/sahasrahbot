"""Presentation-tier coordinator that drives a decomposed tournament event.

Composes a service-tier ``TournamentOrchestrator`` (business) with a Discord
``TournamentPresenter`` (rendering), supplies the Discord-specific resolution the
orchestrator pushes out (player lookup, gatekeeper / async-tournament role checks), and
holds the live RaceTime handler. The discord cog, the RaceTime handler, and the dispatch
module drive a single coordinator object (``construct_race_room`` / ``construct`` /
``construct_with_episode_data`` / ``get_config`` + ``process_tournament_race`` / ``on_*`` /
``can_gatekeep`` / ``player_racetime_ids``).

A coordinator is built from a service-tier ``TournamentEntry`` (orchestrator class +
definition); ``dispatch.py`` resolves the entry from the registry and hands it here. This
replaces the transitional ``OrchestratorAdapter`` + ``make_adapter`` metaprogramming with a
plain presentation-tier class.
"""

import logging
from typing import TYPE_CHECKING

from alttprbot.presentation.discord.bot import discordbot
from alttprbot.presentation.discord.tournament.presenter import TournamentPresenter
from alttprbot.presentation.discord.tournament.config import TournamentConfig
from alttprbot.services._notify import racetime_gateway
from alttprbot.services import AuthorizationService, AuthSubject, UserService
from alttprbot.services.tournament.types import RaceRoom, TournamentPlayer
from alttprbot.exceptions import UnableToLookupUserException

if TYPE_CHECKING:
    from alttprbot.services.tournament.registry import TournamentEntry


class TournamentCoordinator:
    def __init__(self, entry: "TournamentEntry", episodeid=None, rtgg_handler=None):
        self._entry = entry
        self._orchestrator_cls = entry.orchestrator_cls
        self._definition = entry.definition
        try:
            self.episodeid = int(episodeid)
        except TypeError:
            self.episodeid = episodeid
        self.rtgg_handler = rtgg_handler
        self.orchestrator = None
        # `.data` is a live TournamentConfig (resolved from the definition) for the discord
        # cog, which reads live discord objects off the dispatched object (.guild /
        # .audit_channel / .data.scheduling_needs_channel). Built after discordbot is ready
        # (see the construct* / get_config classmethods).
        self.data = None

    # --- construction / dispatch entry points ---
    @classmethod
    async def construct_race_room(cls, entry, episodeid):
        coord = cls(entry, episodeid=episodeid, rtgg_handler=None)
        await discordbot.wait_until_ready()
        coord.data = coord._build_config()
        orch = coord._build_orchestrator(episodeid)
        coord.orchestrator = orch

        # Pre-I/O gate (e.g. alttpr_quals live-race lookup): short-circuit before any
        # SpeedGaming / RaceTime calls, matching the legacy construct_race_room which did
        # its cheap gate first and returned None silently.
        if not await orch.before_update_data():
            return None

        await orch.update_data()

        # Submission gate (e.g. smrl): if the event refuses room creation it has already
        # handled the abort (sent a reminder); skip opening a room.
        if not await orch.before_room_creation():
            return None

        handler = await racetime_gateway.get().start_race(
            entry.definition.racetime_category, **orch.room_creation_kwargs
        )
        handler.tournament = coord
        coord.rtgg_handler = handler

        logging.info(handler.data.get("name"))
        room = coord._room_from_handler(handler)
        await orch.on_room_created(room)
        return handler.data

    @classmethod
    async def construct(cls, entry, episodeid, rtgg_handler):
        coord = cls(entry, episodeid=episodeid, rtgg_handler=rtgg_handler)
        await discordbot.wait_until_ready()
        coord.data = coord._build_config()
        orch = coord._build_orchestrator(episodeid)
        coord.orchestrator = orch
        await orch.update_data()
        if rtgg_handler is not None:
            orch.room = coord._room_from_handler(rtgg_handler)
        return coord

    @classmethod
    async def construct_with_episode_data(cls, entry, episode, rtgg_handler):
        coord = cls(entry, episodeid=episode["id"], rtgg_handler=rtgg_handler)
        await discordbot.wait_until_ready()
        coord.data = coord._build_config()
        orch = coord._build_orchestrator(episode["id"])
        orch.episode = episode
        coord.orchestrator = orch
        await orch.update_data(update_episode=False)
        if rtgg_handler is not None:
            orch.room = coord._room_from_handler(rtgg_handler)
        return coord

    @classmethod
    async def get_config(cls, entry):
        coord = cls(entry, episodeid=None, rtgg_handler=None)
        await discordbot.wait_until_ready()
        coord.data = coord._build_config()
        return coord

    # --- cog-facing surface (the cog reads these live objects off the dispatched object) ---
    @property
    def guild(self):
        return self.data.guild if self.data else None

    @property
    def audit_channel(self):
        return self.data.audit_channel if self.data else None

    @property
    def commentary_channel(self):
        return self.data.commentary_channel if self.data else None

    @property
    def lang(self):
        return self._definition.lang

    @property
    def submission_form(self):
        return self._definition.submission_form

    @property
    def hours_before_room_open(self):
        return (self._definition.stream_delay + self._definition.room_open_time) / 60

    # --- lifecycle interface (delegated to the orchestrator) ---
    async def process_tournament_race(self, args, message):
        # Refresh the room (name / URL) from the live handler before delegating. The
        # entrant list for the post-roll seed-URL whisper is read fresh from the racetime
        # gateway inside process_race (matching the legacy live read), so this snapshot is
        # only used for the room name/URL the orchestrator needs while rolling.
        if self.rtgg_handler is not None:
            self.orchestrator.room = self._room_from_handler(self.rtgg_handler)
        rolled = await self.orchestrator.process_race(args, message)
        # seed_rolled is RaceTime *handler* state guarding double-rolling. The orchestrator
        # (no handler) reports the roll and the coordinator (holds the handler) sets the
        # flag. Only set on success so an exception leaves the room re-rollable.
        if rolled and self.rtgg_handler is not None:
            self.rtgg_handler.seed_rolled = True

    async def on_race_start(self):
        if self.rtgg_handler is not None:
            self.orchestrator.room = self._room_from_handler(self.rtgg_handler)
        await self.orchestrator.on_race_start()

    async def on_race_pending(self):
        await self.orchestrator.on_race_pending()

    async def on_room_resume(self):
        await self.orchestrator.on_room_resume()

    async def on_room_creation(self):
        await self.orchestrator.on_room_creation()

    async def can_gatekeep(self, rtgg_id):
        return await self.orchestrator.can_gatekeep(rtgg_id)

    # --- submission flow (web API + the discord cog's reminder task) ---
    async def process_submission_form(self, payload, submitted_by):
        return await self.orchestrator.process_submission_form(payload, submitted_by)

    async def send_race_submission_form(self, warning=False):
        return await self.orchestrator.send_race_submission_form(warning=warning)

    @property
    def versus(self):
        return self.orchestrator.versus if self.orchestrator else None

    @property
    def player_racetime_ids(self):
        return self.orchestrator.player_racetime_ids if self.orchestrator else []

    # --- wiring helpers ---
    def _build_config(self) -> TournamentConfig:
        """Resolve the TournamentDefinition (IDs) into a live TournamentConfig.

        This is the bridge for the discord cog. The orchestrator itself never uses this —
        it works off the definition.
        """
        d = self._definition
        guild = discordbot.get_guild(d.guild_id) if d.guild_id else None

        def chan(cid):
            return discordbot.get_channel(cid) if cid else None

        def roles(ids):
            if guild is None:
                return []
            return [r for r in (guild.get_role(i) for i in ids) if r is not None]

        return TournamentConfig(
            guild=guild,
            racetime_category=d.racetime_category,
            racetime_goal=d.racetime_goal,
            event_slug=d.event_slug,
            schedule_type=d.schedule_type,
            audit_channel=chan(d.audit_channel_id),
            commentary_channel=chan(d.commentary_channel_id),
            mod_channel=chan(d.mod_channel_id),
            scheduling_needs_channel=chan(d.scheduling_needs_channel_id),
            create_scheduled_events=d.create_scheduled_events,
            scheduling_needs_tracker=d.scheduling_needs_tracker,
            admin_roles=roles(d.admin_role_ids),
            helper_roles=roles(d.helper_role_ids),
            commentator_roles=roles(d.commentator_role_ids),
            mod_roles=roles(d.mod_role_ids),
            stream_delay=d.stream_delay,
            room_open_time=d.room_open_time,
            auto_record=d.auto_record,
            lang=d.lang,
            coop=d.coop,
        )

    def _build_orchestrator(self, episodeid):
        presenter = TournamentPresenter(self._definition)
        return self._orchestrator_cls(
            self._definition,
            episodeid,
            presenter=presenter,
            player_resolver=self._resolve_player,
            gatekeep_checker=self._check_gatekeep,
            async_authz_checker=self._check_async_authz,
        )

    async def _check_async_authz(self, user, tournament, roles):
        """Async-tournament mod/admin check (DB grants + live discord guild roles).

        Resolves the user's roles in the tournament guild here (presentation) and
        delegates the decision to ``AuthorizationService``. Used by the alttpr_quals roll.
        """
        role_ids = frozenset()
        if user is not None:
            guild = discordbot.get_guild(tournament.guild_id)
            if guild is not None:
                if guild.chunked is False:
                    await guild.chunk(cache=True)
                member = guild.get_member(user.discord_user_id)
                if member is not None:
                    role_ids = frozenset(r.id for r in member.roles)
        subject = AuthSubject(
            discord_user_id=user.discord_user_id if user else None,
            discord_role_ids=role_ids,
            user=user,
        )
        return await AuthorizationService().is_async_tournament_user(subject, tournament, roles)

    def _room_from_handler(self, handler) -> RaceRoom:
        category = self._definition.racetime_category
        url = racetime_gateway.get().http_uri(category, handler.data["url"])
        return RaceRoom(
            name=handler.data.get("name"),
            url=url,
            entrant_ids=[e["user"]["id"] for e in handler.data.get("entrants", [])],
        )

    # --- discord-specific resolution the orchestrator delegates back to presentation ---
    async def _resolve_player(self, player):
        guild = discordbot.get_guild(self._definition.guild_id)
        looked_up = None
        if player.get("discordId", "") != "":
            looked_up = await self._player_by_id(player["discordId"], guild)
        if looked_up is None and player.get("discordTag", "") != "":
            looked_up = await self._player_by_name(player["discordTag"], guild)
        if looked_up is None:
            raise UnableToLookupUserException(
                f"Unable to lookup the player `{player['displayName']}`.  "
                "Please contact a Tournament moderator for assistance."
            )
        return looked_up

    async def _player_by_id(self, discord_id, guild):
        if guild is not None and guild.chunked is False:
            await guild.chunk(cache=True)
        user = await UserService().get_by_discord_id(int(discord_id))
        if user is None:
            raise UnableToLookupUserException(f"Unable to pull nick data for {discord_id}")
        member = guild.get_member(int(discord_id)) if guild else None
        # Mirror the legacy path: an unresolved guild member means no room-info DM is
        # attempted (discord_user_id=None -> presenter skips). The RaceTime invite still
        # happens because rtgg_id is set independently.
        return TournamentPlayer(
            rtgg_id=user.rtgg_id,
            name=(member.name if member else None),
            discord_user_id=(member.id if member else None),
        )

    async def _player_by_name(self, discord_name, guild):
        if guild is not None and guild.chunked is False:
            await guild.chunk(cache=True)
        if discord_name.endswith("#0"):
            discord_name = discord_name[:-2]
        member = guild.get_member_named(discord_name) if guild else None
        if member is None:
            raise UnableToLookupUserException(f"Unable to lookup player {discord_name}")
        user = await UserService().get_by_discord_id(member.id)
        if user is None:
            raise UnableToLookupUserException(f"Unable to pull nick data for {discord_name}")
        return TournamentPlayer(rtgg_id=user.rtgg_id, name=member.name, discord_user_id=member.id)

    async def _check_gatekeep(self, discord_user_id, helper_role_ids):
        guild = discordbot.get_guild(self._definition.guild_id)
        if guild is None:
            return False
        if guild.chunked is False:
            await guild.chunk(cache=True)
        member = guild.get_member(discord_user_id)
        if not member:
            return False
        member_role_ids = {r.id for r in member.roles}
        return any(rid in member_role_ids for rid in (helper_role_ids or []))
