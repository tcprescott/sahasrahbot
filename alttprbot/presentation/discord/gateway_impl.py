"""Concrete Discord gateway — the presentation-side implementation of
``alttprbot.services._notify.discord_gateway.DiscordGateway``.

Registered inward at startup so the service tier can reach Discord without importing
the bot singleton or the ``discord`` library. Resolution is lazy (performed when a
method is called), so registering at import time is safe even before the bot is ready.
"""

from __future__ import annotations

from typing import Any, Optional

import aiohttp
import discord

from alttprbot.services._notify import discord_gateway


class DiscordGatewayImpl:
    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot

    # --- sends ---
    async def send_channel_message(
        self,
        channel_id: int,
        content: Optional[str] = None,
        *,
        embed: Any = None,
        mention_everyone: bool = False,
        mention_roles: bool = False,
    ) -> None:
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return
        # ``mention_everyone`` mirrors the legacy ``@here`` audit alerts
        # (``AllowedMentions(everyone=True)``); ``mention_roles`` mirrors the daily-announce
        # ``AllowedMentions(roles=True)``. ``None`` falls back to the client default.
        if mention_everyone:
            allowed_mentions = discord.AllowedMentions(everyone=True)
        elif mention_roles:
            allowed_mentions = discord.AllowedMentions(roles=True)
        else:
            allowed_mentions = None
        await channel.send(content=content, embed=embed, allowed_mentions=allowed_mentions)

    async def send_dm(
        self, user_id: int, content: Optional[str] = None, *, embed: Any = None
    ) -> None:
        user = self.bot.get_user(user_id)
        if user is None:
            user = await self.bot.fetch_user(user_id)
        if user is None:
            return
        await user.send(content=content, embed=embed)

    async def send_webhook(
        self, url: str, *, content: Optional[str] = None, embed: Any = None, username: Optional[str] = None
    ) -> None:
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(url, session=session)
            extra = {"username": username} if username is not None else {}
            await webhook.send(content=content, embed=embed, **extra)

    # --- resolvers ---
    def get_emojis(self) -> list:
        return list(self.bot.emojis)

    def resolve_guild(self, guild_id: int) -> Any:
        return self.bot.get_guild(guild_id)

    def resolve_channel(self, channel_id: int) -> Any:
        return self.bot.get_channel(channel_id)

    def resolve_role(self, guild_id: int, role_id: int) -> Any:
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return None
        return guild.get_role(role_id)

    def resolve_roles(self, guild_id: int, role_ids: list) -> list:
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return []
        return [r for r in (guild.get_role(rid) for rid in role_ids) if r is not None]


def register(bot: discord.Client) -> None:
    discord_gateway.register(DiscordGatewayImpl(bot))
