import os
import random
import string

import aiohttp
import discord
from alttprbot import models
from alttprbot.alttprgen.randomizer.bingosync import BingoSync
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot

from .sglcore import SGLCoreTournamentRace

BINGO_COLLAB_DISCORD_WEBHOOK = os.environ.get('BINGO_COLLAB_DISCORD_WEBHOOK', None)


class SMO(SGLCoreTournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='sgl',
            racetime_goal="Super Mario Galaxy Triple Bingo",
            event_slug="sgl21smo",
            audit_channel=discordbot.get_channel(772351829022474260),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False
        )

    async def on_room_creation(self):
        await self.rtgg_handler.send_message('Setting up bingo cards, please wait...')

        self.bingo = await BingoSync.generate(
            room_name=f"{self.versus} - {self.friendly_name}"[:30],
            passphrase=''.join(random.choice(string.ascii_lowercase) for i in range(8)),
            game_type=45,
            variant_type=45,
            hide_card='on'
        )

        tournamentresults, _ = await models.TournamentResults.update_or_create(srl_id=self.rtgg_handler.data.get('name'), defaults={'episode_id': self.episodeid, 'event': self.event_slug})
        tournamentresults.bingosync_room = self.bingo.room_id
        tournamentresults.bingosync_password = self.bingo.password
        await tournamentresults.save()

        embed = discord.Embed(
            title=f"{self.event_name} - {self.versus}",
            color=discord.Colour.green()
        )

        embed.add_field(name='RaceTime.gg', value=self.rtgg_handler.bot.http_uri(self.rtgg_handler.data['url']), inline=False)

        if self.broadcast_channels:
            embed.add_field(name="Broadcast Channels", value=', '.join([f"[{a}](https://twitch.tv/{a})" for a in self.broadcast_channels]), inline=False)

        embed.add_field(name="BingoSync URL", value=self.bingo.url, inline=False)
        embed.add_field(name="BingoSync Password", value=self.bingo.password, inline=False)

        await self.send_audit_message(embed=embed)

        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(BINGO_COLLAB_DISCORD_WEBHOOK, adapter=discord.AsyncWebhookAdapter(session))
            await webhook.send(embed=embed, username="SahasrahBot")

        await self.rtgg_handler.send_message('Successfully created BingoSync room!')
        await self.rtgg_handler.send_message(f'BingoSync Room: {self.bingo.url}')
        await self.rtgg_handler.send_message(f'BingoSync Password: {self.bingo.password}')

        await self.rtgg_handler.set_raceinfo(f"{self.bingo.url} - Password: {self.bingo.password}")

    async def on_race_start(self):
        await self.bingo.new_card(
            game_type=45,
            variant_type=45,
            hide_card='off',
        )

    async def on_room_resume(self):
        res = await models.TournamentResults.get_or_none(srl_id=self.rtgg_handler.data.get('name'))
        if res is None or res.bingosync_room is None or res.bingosync_password is None:
            await self.on_room_creation()
        else:
            self.bingo = await BingoSync.retrieve(
                room_id=res.bingosync_room,
                password=res.bingosync_password
            )
