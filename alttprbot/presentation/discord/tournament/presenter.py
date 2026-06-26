"""``TournamentPresenter`` — Discord rendering + sends for the tournament orchestrator.

The orchestrator (service tier) hands this presenter presentation-neutral data
(``SeedResult``, plain strings, user/role/channel IDs from the ``TournamentDefinition``)
and the presenter builds embeds and performs Discord sends through the discord gateway.
It is the home for the embed/DM/audit/commentary logic that used to live on the
``TournamentRace`` god-object (``send_audit_message`` / ``send_commentary_message`` /
``send_player_message`` / ``send_player_room_info`` / ``create_embeds``).

Behavior is preserved from the legacy base methods; the channel/role resolution that
used hardcoded ``discordbot.get_channel(<id>)`` now reads the IDs off the definition and
resolves them through the gateway.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Optional, Tuple

import discord

from alttprbot.presentation.discord.util.seed_embeds import seed_embed, seed_tournament_embed
from alttprbot.services._notify import discord_gateway
from alttprbot.services.tournament import SeedResult, TournamentDefinition


class TournamentPresenter:
    def __init__(self, definition: TournamentDefinition, gateway: Any = None) -> None:
        self.definition = definition
        self._gateway = gateway

    @property
    def gateway(self) -> Any:
        # resolve lazily so a presenter can be constructed before the bot registers
        return self._gateway if self._gateway is not None else discord_gateway.get()

    # --- seed embeds (neutral SeedResult -> discord.Embed) ---
    async def build_seed_embeds(
        self,
        result: SeedResult,
        *,
        race_info: Any = False,
        versus: Any = False,
        include_settings: bool = True,
    ) -> Tuple[discord.Embed, discord.Embed]:
        """Return ``(embed, tournament_embed)`` for a generated seed.

        Mirrors the legacy ``ALTTPRTournamentRace.create_embeds`` pair: a public embed
        (``seed_embed``) and the restream/tournament embed (``seed_tournament_embed``).
        """
        emojis = self.gateway.get_emojis()
        embed = await seed_embed(
            result.seed, emojis=emojis, name=race_info, notes=versus, include_settings=include_settings
        )
        tournament_embed = await seed_tournament_embed(
            result.seed, emojis=emojis, name=race_info, notes=versus, include_settings=include_settings
        )
        return embed, tournament_embed

    # --- channel sends ---
    async def send_audit_message(self, content: Optional[str] = None, embed: discord.Embed = None) -> None:
        if self.definition.audit_channel_id:
            await self.gateway.send_channel_message(self.definition.audit_channel_id, content, embed=embed)

    async def send_commentary_message(self, embed: discord.Embed, *, has_broadcasts: bool) -> None:
        if self.definition.commentary_channel_id and has_broadcasts:
            await self.gateway.send_channel_message(self.definition.commentary_channel_id, embed=embed)

    # --- player DMs ---
    async def send_player_room_info(self, player_ids: Iterable[int], *, versus: str, room_url: str) -> None:
        """DM each player that their RaceTime room has opened (legacy ``send_player_room_info``)."""
        embed = discord.Embed(
            title=f"RT.gg Room Opened - {versus}",
            description=(
                "Greetings!  A RaceTime.gg race room has been automatically opened for you.\n"
                f"You may access it at {room_url}\n\nEnjoy!"
            ),
            color=discord.Colour.blue(),
            timestamp=discord.utils.utcnow(),
        )
        for player_id in player_ids:
            if player_id is None:
                logging.info("Could not DM player (unresolved discord member)")
                continue
            try:
                await self.gateway.send_dm(player_id, embed=embed)
            except discord.HTTPException:
                logging.info("Could not send room opening DM to %s", player_id)

    async def send_player_dm(self, user_id: int, *, content: Optional[str] = None, embed: discord.Embed = None) -> None:
        await self.gateway.send_dm(user_id, content, embed=embed)
