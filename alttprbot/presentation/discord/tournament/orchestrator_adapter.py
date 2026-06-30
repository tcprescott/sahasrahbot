"""Transitional adapter bridging the legacy dispatch to the decomposed orchestrator.

The discord cog, RaceTime handler, and ``tournaments.py`` dispatch all drive a
``TournamentRace``-shaped object (``construct_race_room`` / ``construct`` /
``construct_with_episode_data`` / ``get_config`` classmethods + ``process_tournament_race``
/ ``on_*`` / ``can_gatekeep`` / ``player_racetime_ids``). This adapter presents that exact
interface but delegates business to a ``TournamentOrchestrator`` (service tier) and
rendering/sends to a ``TournamentPresenter`` (discord presentation).

It lives in the Discord presentation tier (``presentation/discord/tournament/``) because it
touches ``discordbot`` for the Discord-specific resolution the orchestrator pushes out
(player lookup, gatekeeper role checks) and holds the live RaceTime handler. ``tournaments.py``
builds the per-event registry by binding each orchestrator class to this adapter via
:func:`make_adapter`; every active event slug now resolves to a decomposed
``(orchestrator, presenter)`` pair behind this interface.
"""

import logging

from alttprbot.presentation.discord.bot import discordbot
from alttprbot.presentation.discord.tournament.presenter import TournamentPresenter
from alttprbot.presentation.discord.tournament.config import TournamentConfig
from alttprbot.services._notify import racetime_gateway
from alttprbot.services import UserService
from alttprbot.services.tournament.types import RaceRoom, TournamentPlayer
from alttprbot.exceptions import UnableToLookupUserException


class OrchestratorAdapter:
    # set by make_adapter() on each per-event subclass
    _orchestrator_cls = None
    _definition = None

    def __init__(self, episodeid=None, rtgg_handler=None):
        try:
            self.episodeid = int(episodeid)
        except TypeError:
            self.episodeid = episodeid
        self.rtgg_handler = rtgg_handler
        self.orchestrator = None
        # `.data` is a live TournamentConfig (resolved from the definition) for backward
        # compatibility with the un-migrated discord cog, which reads live discord objects
        # off the dispatched object (.guild / .audit_channel / .data.scheduling_needs_channel).
        # Built after discordbot is ready (see the construct* / get_config classmethods).
        self.data = None

    # --- construction / dispatch entry points ---
    @classmethod
    async def construct_race_room(cls, episodeid):
        adapter = cls(episodeid=episodeid, rtgg_handler=None)
        await discordbot.wait_until_ready()
        adapter.data = adapter._build_config()
        orch = adapter._build_orchestrator(episodeid)
        adapter.orchestrator = orch

        # Pre-I/O gate (e.g. alttpr_quals live-race lookup): short-circuit before any
        # SpeedGaming / RaceTime calls, matching the legacy construct_race_room which did
        # its cheap gate first and returned None silently.
        if not await orch.before_update_data():
            return None

        await orch.update_data()

        # Submission gate (e.g. smrl): if the event refuses room creation it has already
        # handled the abort (sent a reminder); skip opening a room. This cleanly drops a
        # latent legacy crash — legacy create_race_room returned None here, which the
        # un-null-checked base construct_race_room dereferenced (AttributeError + a spurious
        # "error creating a race room" audit message). Warning DMs + the upsert are unchanged.
        if not await orch.before_room_creation():
            return None

        handler = await racetime_gateway.get().start_race(
            cls._definition.racetime_category, **orch.room_creation_kwargs
        )
        handler.tournament = adapter
        adapter.rtgg_handler = handler

        logging.info(handler.data.get("name"))
        room = adapter._room_from_handler(handler)
        await orch.on_room_created(room)
        return handler.data

    @classmethod
    async def construct(cls, episodeid, rtgg_handler):
        adapter = cls(episodeid=episodeid, rtgg_handler=rtgg_handler)
        await discordbot.wait_until_ready()
        adapter.data = adapter._build_config()
        orch = adapter._build_orchestrator(episodeid)
        adapter.orchestrator = orch
        await orch.update_data()
        if rtgg_handler is not None:
            orch.room = adapter._room_from_handler(rtgg_handler)
        return adapter

    @classmethod
    async def construct_with_episode_data(cls, episode, rtgg_handler):
        adapter = cls(episodeid=episode["id"], rtgg_handler=rtgg_handler)
        await discordbot.wait_until_ready()
        adapter.data = adapter._build_config()
        orch = adapter._build_orchestrator(episode["id"])
        orch.episode = episode
        adapter.orchestrator = orch
        await orch.update_data(update_episode=False)
        if rtgg_handler is not None:
            orch.room = adapter._room_from_handler(rtgg_handler)
        return adapter

    @classmethod
    async def get_config(cls):
        adapter = cls(episodeid=None, rtgg_handler=None)
        await discordbot.wait_until_ready()
        adapter.data = adapter._build_config()
        return adapter

    # --- backward-compat surface for the un-migrated discord cog ---
    # The cog reads these live objects off the dispatched object (post get_config).
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

    # --- legacy instance interface (delegated to the orchestrator) ---
    async def process_tournament_race(self, args, message):
        # Refresh the room (name / URL) from the live handler before delegating. The
        # entrant list for the post-roll seed-URL whisper is read fresh from the racetime
        # gateway inside process_race (matching the legacy live read), so this snapshot is
        # only used for the room name/URL the orchestrator needs while rolling.
        if self.rtgg_handler is not None:
            self.orchestrator.room = self._room_from_handler(self.rtgg_handler)
        rolled = await self.orchestrator.process_race(args, message)
        # seed_rolled is RaceTime *handler* state guarding double-rolling. The legacy
        # subclasses set it as the last line of a successful process_tournament_race; the
        # orchestrator (no handler) reports the roll and the adapter (holds the handler)
        # sets the flag. Only set on success so an exception leaves the room re-rollable.
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

        This is the backward-compat bridge for the un-migrated cog. The orchestrator
        itself never uses this — it works off the definition.
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
        """Async-tournament mod/admin check (DB + discord guild roles).

        Wraps the existing ``checks.is_async_tournament_user`` (which touches ``discordbot``);
        imported lazily to keep this off the module import path. Used by the alttpr_quals roll.
        """
        from alttprbot.presentation.api.util import checks
        return await checks.is_async_tournament_user(user, tournament, roles)

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


def make_adapter(orchestrator_cls, definition):
    """Build a per-event adapter class bound to an orchestrator class + definition."""
    return type(
        f"{orchestrator_cls.__name__}Adapter",
        (OrchestratorAdapter,),
        {"_orchestrator_cls": orchestrator_cls, "_definition": definition},
    )
