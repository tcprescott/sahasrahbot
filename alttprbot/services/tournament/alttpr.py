"""``ALTTPRTournamentOrchestrator`` — the ALTTPR-family business core.

A behavior-preserving port of the legacy ``alttprbot/tournament/alttpr.py``
``ALTTPRTournamentRace`` (the shared base of ``boots`` / ``alttprde`` / ``alttprmini``
/ ``alttprhmg`` / ``nologic`` and friends). It owns the seed-rolling lifecycle that
the generic ALTTPR tournaments share:

- ``process_race`` — the ``!tournamentrace`` flow: announce, (re)load data, ``roll`` a
  seed, render embeds (via the presenter), set the RaceTime race-info, post to
  audit/commentary, DM each player with a cross-gateway fallback, DM the seed URL to
  each entrant, persist the permalink, and announce completion.
- ``send_room_welcome`` — the room-open welcome message + the pinned "Roll Tournament
  Seed" action button.
- ``seed_code`` — the bot race-info string ``(a/b/c/...)`` from the seed hash.

Every Discord/RaceTime concern is pushed out to the injected ``presenter`` and
``racetime`` gateway; concrete events (``boots`` etc.) override only :meth:`roll`.
This module imports no ``discord`` / ``racetime_bot`` / ``alttprbot.presentation``.
"""

from __future__ import annotations

from alttprbot.repositories import TournamentResultsRepository
from alttprbot.services.tournament.core import TournamentOrchestrator
from alttprbot.services.tournament.types import SeedResult


class ALTTPRTournamentOrchestrator(TournamentOrchestrator):
    """Generic ALTTPR tournament: seed-roll lifecycle shared by the ALTTPR events."""

    async def roll(self) -> SeedResult:
        """Generate the seed for this race. Concrete events must override.

        Mirrors the legacy ``ALTTPRTournamentRace.roll`` (a no-op base; each event
        supplies its preset). Returns the neutral :class:`SeedResult` the presenter and
        persistence layer consume.
        """
        raise NotImplementedError("ALTTPR tournament events must override roll().")

    @staticmethod
    def _seed_code(result: SeedResult) -> str:
        """The RaceTime bot race-info string, e.g. ``(Bow/Boots/Bombs/...)``.

        Ports ``ALTTPRTournamentRace.seed_code`` (``f"({'/'.join(self.seed.code)})"``).
        """
        return f"({'/'.join(result.seed.code)})"

    async def send_room_welcome(self) -> None:
        room = self.room.name
        await self.racetime.send_message(
            room,
            'Welcome! Use the "Roll Tournament Seed" pinned above about 5 minutes before '
            'your race start.  You do NOT need to wait for your setup helper to do this or '
            'start your race, they will appear later to setup the stream.',
        )
        await self.racetime.send_pinned_action(
            room,
            "Tournament Controls:",
            label="Roll Tournament Seed",
            help_text=(
                "Create a seed for this specific tournament race.  This should only be "
                "done shortly before the race starts."
            ),
            message="!tournamentrace",
        )

    async def process_race(self, args, message) -> bool:
        room = self.room.name
        await self.racetime.send_message(
            room,
            "Generating game, please wait.  If nothing happens after a minute, contact Synack.",
        )

        await self.update_data()
        result = await self.roll()

        embed, tournament_embed = await self.presenter.build_race_embeds(
            result,
            race_info=self.race_info,
            versus=self.versus,
            room_url=self.room.url,
            broadcast_channels=self.broadcast_channels,
        )

        await self.racetime.set_bot_raceinfo(room, self._seed_code(result))

        await self.presenter.send_audit_message(embed=embed)
        await self.presenter.send_commentary_message(
            tournament_embed, has_broadcasts=bool(self.broadcast_channels)
        )

        for player in self.players:
            delivered = await self.presenter.send_player_seed_dm(player.discord_user_id, embed=embed)
            if not delivered:
                await self.presenter.send_audit_alert(f"@here could not send DM to {player.name}")
                await self.racetime.send_message(
                    room,
                    f"Could not send DM to {player.name}.  Please contact a Tournament "
                    "Moderator for assistance.",
                )

        # Whisper the seed URL to the CURRENT entrants, read fresh after the roll — the
        # legacy path read self.rtgg_handler.data['entrants'] here (post-roll/live), so a
        # player who joined/left during seed generation is included/excluded accordingly.
        for entrant_id in await self.racetime.get_entrant_ids(room):
            await self.racetime.send_message(room, result.url, direct_to=entrant_id)

        await TournamentResultsRepository.create_or_update_with_permalink(
            srl_id=room,
            defaults={"episode_id": self.episodeid, "event": self.event_slug, "spoiler": None},
            permalink=result.url,
        )

        await self.racetime.send_message(
            room,
            "Seed has been generated, you should have received a DM in both Discord and "
            "RaceTime.gg.  Please contact a Tournament Moderator if you haven't received the DM.",
        )
        return True
