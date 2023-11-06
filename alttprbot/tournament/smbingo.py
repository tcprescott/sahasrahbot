import random
import string

import aiohttp
import discord

import config
from alttprbot import models
from alttprbot.alttprgen.randomizer.bingosync import BingoSync
from alttprbot.tournament.core import TournamentRace, TournamentConfig
from alttprbot_discord.bot import discordbot

BINGO_COLLAB_DISCORD_WEBHOOK = config.BINGO_COLLAB_DISCORD_WEBHOOK


class SMBingoTournament(TournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(155487315530088448)
        return TournamentConfig(
            guild=guild,
            racetime_category='sm',
            racetime_goal='Triple Bingo',
            event_slug="smbingo",
            audit_channel=discordbot.get_channel(871187586687856670),
            helper_roles=[
                guild.get_role(404395533482983447),
                guild.get_role(338121128004288513),
                guild.get_role(173917459785449472),
            ]
        )

    async def send_room_welcome(self):
        await self.rtgg_handler.send_message('Welcome!  You may start your race when ready.  A link to the bingo card will be posted in chat once the race starts.')

    async def on_room_creation(self):
        await self.rtgg_handler.send_message('Setting up bingo cards, please wait...')

        self.bingo = await BingoSync.generate(
            room_name=f"{self.versus} - {self.friendly_name}"[:30],
            passphrase=''.join(random.choice(string.ascii_lowercase) for i in range(8)),
            game_type=4,
            variant_type=4,
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

        await self.rtgg_handler.send_message('BingoSync room has been created and sent to SpeedGaming for setup!')

    async def on_race_start(self):
        bingoseed = random.randint(0, 899999)
        await self.rtgg_handler.send_message(f"-----------------------")
        await self.rtgg_handler.send_message(f"https://www.speedrunslive.com/tools/supermetroid-bingo/?seed={bingoseed}")
        await self.rtgg_handler.send_message(f"-----------------------")

        await self.bingo.new_card(
            game_type=4,
            variant_type=4,
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
