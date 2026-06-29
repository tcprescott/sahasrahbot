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

    async def build_race_embeds(
        self,
        result: SeedResult,
        *,
        race_info: Any,
        versus: Any,
        room_url: str,
        broadcast_channels: Iterable[str],
    ) -> Tuple[discord.Embed, discord.Embed]:
        """Build the seed embeds for a rolled tournament race, with the live-room inserts.

        Mirrors the legacy ``ALTTPRTournamentRace.create_embeds``: the standard pair
        plus a ``RaceTime.gg`` field (the room URL) inserted at the top of each, and a
        ``Broadcast Channels`` field inserted above that when there are restreams.
        ``insert_field_at(0, ...)`` is order-sensitive, so the RaceTime.gg field is
        inserted first and the broadcast field second — leaving the final order
        ``[Broadcast Channels?, RaceTime.gg, ...settings]`` exactly as before.
        """
        embed, tournament_embed = await self.build_seed_embeds(
            result, race_info=race_info, versus=versus
        )
        for e in (tournament_embed, embed):
            e.insert_field_at(0, name="RaceTime.gg", value=room_url, inline=False)
        channels = list(broadcast_channels)
        if channels:
            links = ", ".join(f"[{a}](https://twitch.tv/{a})" for a in channels)
            for e in (tournament_embed, embed):
                e.insert_field_at(0, name="Broadcast Channels", value=links, inline=False)
        return embed, tournament_embed

    # --- channel sends ---
    async def send_audit_message(self, content: Optional[str] = None, embed: discord.Embed = None) -> None:
        if self.definition.audit_channel_id:
            await self.gateway.send_channel_message(self.definition.audit_channel_id, content, embed=embed)

    async def send_audit_alert(self, content: str) -> None:
        """Post an ``@here`` audit alert (legacy DM-failure notice).

        No-ops when no audit channel is configured. The legacy code unconditionally
        sent to ``self.audit_channel`` here and would crash if it was ``None``; guarding
        on the configured id is strictly safer and consistent with ``send_audit_message``.
        """
        if self.definition.audit_channel_id:
            await self.gateway.send_channel_message(
                self.definition.audit_channel_id, content, mention_everyone=True
            )

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

    async def send_player_reminders(self, player_ids: Iterable[Optional[int]], message: str) -> None:
        """DM each resolved player a plain-text reminder (legacy ``send_race_submission_form``).

        Unresolved members (``None``) are skipped. Delivery failures are NOT caught — they
        propagate, exactly as the legacy ``await player.send(msg)`` did (the discord cog's
        ``send_race_form`` is the surrounding try/except that logs + audits).
        """
        for player_id in player_ids:
            if player_id is None:
                continue
            logging.info("Sending tournament submit reminder to %s.", player_id)
            await self.gateway.send_dm(player_id, message)

    async def send_submission_confirmation(
        self,
        *,
        versus: str,
        episode_id: Any,
        event: str,
        game_number: Any,
        randomizer: str,
        preset: str,
        submitted_by: str,
        players: Iterable[Tuple[Optional[str], Optional[int]]],
    ) -> None:
        """Build + broadcast the SMRL settings-submission confirmation embed.

        Mirrors the legacy ``SMRLPlayoffs.process_submission_form`` presentation half:
        post the summary embed to the audit channel and DM it to each player, with an
        ``@here`` audit alert (carrying the embed) when a player can't be DMed.
        """
        embed = discord.Embed(
            title=f"SMRL - {versus}",
            description=(
                "Thank you for submitting your settings for this race!  Below is what will be "
                "played.\nIf this is incorrect, please contact a tournament admin."
            ),
            color=discord.Colour.blue(),
        )
        embed.add_field(name="Episode ID", value=episode_id, inline=False)
        embed.add_field(name="Event", value=event, inline=False)
        embed.add_field(name="Game #", value=game_number, inline=False)
        embed.add_field(name="Randomizer", value=randomizer, inline=False)
        embed.add_field(name="Preset", value=preset, inline=False)
        embed.add_field(name="Submitted by", value=submitted_by, inline=False)

        if self.definition.audit_channel_id:
            await self.gateway.send_channel_message(self.definition.audit_channel_id, embed=embed)

        for name, user_id in players:
            if user_id is None:
                logging.error("Could not send DM to %s", name)
                await self._submission_dm_failed(name, embed)
                continue
            try:
                await self.gateway.send_dm(user_id, embed=embed)
            except discord.HTTPException:
                logging.exception("Could not send DM to %s", name)
                await self._submission_dm_failed(name, embed)

    async def _submission_dm_failed(self, name: Optional[str], embed: discord.Embed) -> None:
        if self.definition.audit_channel_id:
            await self.gateway.send_channel_message(
                self.definition.audit_channel_id,
                f"@here could not send DM to {name}",
                embed=embed,
                mention_everyone=True,
            )

    async def send_player_seed_dm(self, user_id: Optional[int], *, embed: discord.Embed) -> bool:
        """DM a player their seed embed, returning whether delivery succeeded.

        Mirrors the legacy ``send_player_message`` delivery half: an unresolved member
        (``user_id is None``) or a ``discord.HTTPException`` is a failed delivery. The
        orchestrator owns the cross-gateway failure handling (audit ``@here`` alert +
        RaceTime chat notice), so this only reports success/failure.
        """
        if user_id is None:
            return False
        try:
            await self.gateway.send_dm(user_id, embed=embed)
            return True
        except discord.HTTPException:
            return False
