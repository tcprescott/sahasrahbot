import logging

import discord
from werkzeug.datastructures import MultiDict

from alttprbot import models
from alttprbot.alttprgen.randomizer import smdash
from alttprbot.tournament.core import TournamentConfig, TournamentRace
from alttprbot_discord.bot import discordbot
from alttprbot_discord.util.smvaria_discord import SuperMetroidVariaDiscord

# game schedule
# 1. Chozo, Vanilla Area, Boss Shuffle - RLS4W5
# 2. DASH recall - recall_mm
# 3. Countdown, Full Area, Boss Shuffle - RLS4GS
# 4 and 5: Choice of following
# - Countdown, Full Area, Vanilla Bosses (week 2) - RLS4W2
# - Major/Minor, Full Area, Boss Shuffle (week 3) - RLS4W3
# - Countdown, Vanilla Area, Boss Shuffle (countdown equivalent to week 4) - RLS4P1
# - Classic DASH - standard_mm
# - Chozo, Full Area, Vanilla Bosses - RLS4P2


class SMRLPlayoffs(TournamentRace):
    async def process_tournament_race(self, args, message):
        await self.rtgg_handler.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")

        await self.update_data()

        # await self.rtgg_handler.set_bot_raceinfo(self.seed_code)

        # await self.send_audit_message(embed=self.embed)

        tournamentresults, _ = await models.TournamentResults.update_or_create(srl_id=self.rtgg_handler.data.get('name'), defaults={'episode_id': self.episodeid, 'event': self.event_slug, 'spoiler': None})

        randomizer = self.tournament_game.settings['randomizer']
        preset = self.tournament_game.settings['preset']

        if randomizer == 'smvaria':
            self.seed = await SuperMetroidVariaDiscord.create(
                settings_preset=preset,
                skills_preset="Season_Races",
                race=True
            )
            await self.rtgg_handler.send_message(self.seed.url)
            await self.rtgg_handler.set_bot_raceinfo(self.seed.url)
            tournamentresults.permalink = self.seed.url

        elif randomizer == 'smdash':
            self.seed = await smdash.create_smdash(
                mode=preset,
                encrypt=True,
            )
            await self.rtgg_handler.send_message(self.seed)
            await self.rtgg_handler.set_bot_raceinfo(self.seed)
            tournamentresults.permalink = self.seed

        await tournamentresults.save()

        await self.rtgg_handler.send_message("Seed has been generated!")
        self.rtgg_handler.seed_rolled = True

    async def send_room_welcome(self):
        await self.rtgg_handler.send_message('Welcome. Use !tournamentrace (without any arguments) to roll your seed!  This should be done about 5 minutes prior to the start of your race.  You do NOT need to wait for your setup helper to do this or start your race, they will appear later to setup the stream.')

    async def send_audit_message(self, message=None, embed: discord.Embed = None):
        if self.audit_channel:
            await self.audit_channel.send(content=message, embed=embed)

    @property
    def submission_form(self):
        return "submission_smrl.html"

    async def configuration(self):
        guild = discordbot.get_guild(500362417629560881)
        return TournamentConfig(
            guild=guild,
            racetime_category='smr',
            racetime_goal='Beat the game',
            event_slug="smrl",
            audit_channel=discordbot.get_channel(1080994224880750682),
            helper_roles=[
                guild.get_role(500363025958567948),
                guild.get_role(501810831504179250),
                guild.get_role(504725352745140224)
            ],
        )

    async def create_race_room(self):
        if self.tournament_game is None or self.tournament_game.settings is None:
            await self.send_race_submission_form(warning=True)
            # raise Exception(f"Could not open `{self.episodeid}` because setttings were not submitted.")
            return

        self.rtgg_handler = await self.rtgg_bot.startrace(
            goal=self.data.racetime_goal,
            invitational=True,
            unlisted=False,
            info_user=self.race_info,
            start_delay=15,
            time_limit=24,
            streaming_required=True,
            auto_start=True,
            allow_comments=True,
            hide_comments=True,
            allow_prerace_chat=True,
            allow_midrace_chat=True,
            allow_non_entrant_chat=False,
            chat_message_delay=0,
            team_race=False,
        )
        return self.rtgg_handler

    async def process_submission_form(self, payload: MultiDict, submitted_by: str):
        embed = discord.Embed(
            title=f"SMRL - {self.versus}",
            description='Thank you for submitting your settings for this race!  Below is what will be played.\nIf this is incorrect, please contact a tournament admin.',
            color=discord.Colour.blue()
        )

        game_number = int(payload['game'])

        if game_number == 1:
            randomizer = 'smvaria'
            preset = 'RLS4W5'
        elif game_number == 2:
            randomizer = 'smdash'
            preset = 'recall_mm'
        elif game_number == 3:
            randomizer = 'smvaria'
            preset = 'RLS4GS'
        elif game_number in [4, 5]:
            preset = payload['preset']
            randomizer = 'smdash' if preset == 'standard_mm' else 'smvaria'

        embed.add_field(name="Episode ID", value=self.episodeid, inline=False)
        embed.add_field(name="Event", value=self.event_slug, inline=False)
        embed.add_field(name="Game #", value=game_number, inline=False)
        embed.add_field(name="Randomizer", value=randomizer, inline=False)
        embed.add_field(name="Preset", value=preset, inline=False)
        embed.add_field(name="Submitted by", value=submitted_by, inline=False)

        settings = {
            'randomizer': randomizer,
            'preset': preset
        }

        await models.TournamentGames.update_or_create(episode_id=self.episodeid, defaults={'settings': settings, 'event': self.event_slug, 'game_number': game_number})

        if self.audit_channel:
            await self.audit_channel.send(embed=embed)

        for name, player in self.player_discords:
            if player is None:
                logging.error("Could not send DM to %s", name)
                if self.audit_channel:
                    await self.audit_channel.send(f"@here could not send DM to {name}", allowed_mentions=discord.AllowedMentions(everyone=True), embed=embed)
                continue
            try:
                await player.send(embed=embed)
            except discord.HTTPException:
                logging.exception("Could not send DM to %s", name)
                if self.audit_channel:
                    await self.audit_channel.send(f"@here could not send DM to {player.name}#{player.discriminator}", allowed_mentions=discord.AllowedMentions(everyone=True), embed=embed)

def get_embed_field(name: str, embed: discord.Embed) -> str:
    for field in embed.fields:
        if field.name == name:
            return field.value
    return None
