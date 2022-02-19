import string
import random
import os

import aiohttp
import discord

from alttprbot.alttprgen.randomizer.bingosync import BingoSync
from alttprbot import models
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot
from .sglcore import SGLRandomizerTournamentRace

BINGO_COLLAB_DISCORD_WEBHOOK = os.environ.get('BINGO_COLLAB_DISCORD_WEBHOOK', None)


class Bloodstained(SGLRandomizerTournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='sgl',
            racetime_goal="Bloodstained RotN Rando Bingo",
            event_slug="sgl21bloodstained",
            audit_channel=discordbot.get_channel(772351829022474260),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False,
            gsheet_id=os.environ.get("SGL_RESULTS_SHEET"),
            auto_record=True
        )

    @property
    def seed_info(self):
        return self.seed_url

    @property
    def seed_url(self):
        return f"https://sahasrahbot.s3.amazonaws.com/brotn/{self.patch_id}"

    async def roll(self):
        patches = await models.PatchDistribution.filter(game='brotn', used=None)
        patch = random.choice(patches)
        self.patch_id = patch.patch_id
        patch.used = 1
        await patch.save()

        await self.bingo.new_card(
            game_type=227,
            hide_card='on'
        )

    async def create_race_room(self):
        self.rtgg_handler = await self.rtgg_bot.startrace(
            goal=self.data.racetime_goal,
            invitational=False,
            unlisted=True,
            info_user=self.race_info,
            start_delay=30,
            time_limit=24,
            streaming_required=True,
            auto_start=True,
            allow_comments=True,
            hide_comments=True,
            allow_prerace_chat=True,
            allow_midrace_chat=True,
            allow_non_entrant_chat=False,
            chat_message_delay=0,
            team_race=self.data.coop,
        )
        return self.rtgg_handler

    async def on_room_creation(self):
        await self.rtgg_handler.send_message('Setting up bingo cards, please wait...')

        self.bingo = await BingoSync.generate(
            room_name=f"{self.versus} - {self.friendly_name}"[:30],
            passphrase=''.join(random.choice(string.ascii_lowercase) for i in range(8)),
            game_type=227,
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
            webhook = discord.Webhook.from_url(BINGO_COLLAB_DISCORD_WEBHOOK, session=session)
            await webhook.send(embed=embed, username="SahasrahBot")

        await self.rtgg_handler.send_message('Successfully sent BingoSync room to SpeedGaming for setup!')

    async def on_race_pending(self):
        bingoseed = random.randint(10000, 99999)
        await self.rtgg_handler.send_message(f"-----------------------")
        await self.rtgg_handler.send_message(f"The seed for this race: {bingoseed}")
        await self.rtgg_handler.send_message(f"-----------------------")

        await self.bingo.new_card(
            game_type=227,
            hide_card='off',
            seed=bingoseed,
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
