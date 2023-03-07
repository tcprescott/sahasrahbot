import random

import discord

from alttprbot import models
from alttprbot.alttprgen import smz3multi
from alttprbot.alttprgen.randomizer import smdash
from alttprbot.tournament.core import TournamentConfig, TournamentRace
from alttprbot_discord.bot import discordbot
from alttprbot_discord.util.smvaria_discord import SuperMetroidVariaDiscord

# tournament schedule
# 1. Multiworld with major/minor split https: // sm.samus.link/
# 2. Countdown, Full Area, Vanilla Bosses
# 3. Major/Minor, Full Area, Boss Shuffle
# 4. Coop: Full Item Shuffle, Vanilla Area, Boss Shuffle
# 5. Chozo, Vanilla Area, Boss Shuffle
# 6. DASH recall https: // dashrando.github.io/
# 7. Coop: Full Item Shuffle, Full Area Shuffle, Boss Shuffle

WEEK = 1

WEEKS = {
    1: {
        'name': 'Multiworld Major/Minor Split',
        'preset': 'tournament_split',
        'coop': True,
        'randomizer': 'smmulti'
    },
    2: {
        'name': 'Countdown, Full Area, Vanilla Bosses',
        'preset': 'RLS4W2',
        'coop': False,
        'randomizer': 'smvaria'
    },
    3: {
        'name': 'Major/Minor, Full Area, Boss Shuffle',
        'preset': 'RLS4W3',
        'coop': False,
        'randomizer': 'smvaria'
    },
    4: {
        'name': 'Coop: Full Item Shuffle, Vanilla Area, Boss Shuffle',
        'preset': 'RLS4W4',
        'coop': True,
        'randomizer': 'smvaria'
    },
    5: {
        'name': 'Chozo, Vanilla Area, Boss Shuffle',
        'preset': 'RLS4W5',
        'coop': False,
        'randomizer': 'smvaria'
    },
    6: {
        'name': 'DASH Recall',
        'preset': 'mm',
        'coop': False,
        'randomizer': 'smdash'
    },
    7: {
        'name': 'Coop: Full Item Shuffle, Full Area Shuffle, Boss Shuffle',
        'preset': 'RLS4W7',
        'coop': True,
        'randomizer': 'smvaria'
    }
}


class SMRandoLeague(TournamentRace):
    async def process_tournament_race(self):
        await self.rtgg_handler.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")

        await self.update_data()

        # await self.rtgg_handler.set_bot_raceinfo(self.seed_code)

        # await self.send_audit_message(embed=self.embed)

        tournamentresults, _ = await models.TournamentResults.update_or_create(srl_id=self.rtgg_handler.data.get('name'), defaults={'episode_id': self.episodeid, 'event': self.event_slug, 'spoiler': None})

        if WEEKS[WEEK].get('randomizer') == 'smmulti':
            if len(self.player_names) != 4:
                await self.rtgg_handler.send_message("This week's races require 4 players.  Please contact a Tournament Moderator if you need assistance.")
                return
            self.seed, seeds = await self.create_multiworld()
            tournamentresults.permalink = self.seed

        elif WEEKS[WEEK].get('randomizer') == 'smvaria':
            self.seed = await SuperMetroidVariaDiscord.create(
                settings_preset=WEEKS[WEEK].get('preset'),
                skills_preset="Season_Races",
                race=True
            )
            await self.rtgg_handler.send_message(self.seed.url)
            await self.rtgg_handler.set_bot_raceinfo(self.seed.url)
            tournamentresults.permalink = self.seed.url

        elif WEEKS[WEEK].get('randomizer') == 'smdash':
            self.seed = await smdash.create_smdash(
                mode=WEEKS[WEEK].get('preset'),
                encrypt=True,
            )
            await self.rtgg_handler.send_message(self.seed)
            await self.rtgg_handler.set_bot_raceinfo(self.seed)
            tournamentresults.permalink = self.seed

        await tournamentresults.save()

        await self.rtgg_handler.send_message("Seed has been generated, you should have received a DM in Discord.  Please contact a Tournament Moderator if you haven't received the DM.")
        self.rtgg_handler.seed_rolled = True

    async def create_multiworld(self):
        seed_number = random.randint(0, 2147483647)
        player_names = self.player_names
        teams = [
            [player_names[0], player_names[2]],
            [player_names[1], player_names[3]]
        ]
        seeds = []
        for team in teams:
            seed = await smz3multi.generate_multiworld(
                preset=WEEKS[WEEK].get('preset'),
                tournament=True,
                randomizer='sm',
                seed_number=seed_number,
                players=team,
            )
            await self.rtgg_handler.send_message(f"{', '.join(team)}: {seed.url}")
            await self.rtgg_handler.send_message("-------------------")
            seeds.append(seed)

        return seed_number, seeds

    async def send_room_welcome(self):
        await self.rtgg_handler.send_message('Welcome. Use !tournamentrace (without any arguments) to roll your seed!  This should be done about 5 minutes prior to the start of your race.  You do NOT need to wait for your setup helper to do this or start your race, they will appear later to setup the stream.')

    async def send_audit_message(self, message=None, embed: discord.Embed = None):
        if self.audit_channel:
            await self.audit_channel.send(content=message, embed=embed)

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
            team_race=WEEKS[WEEK].get('coop', False),
        )
        return self.rtgg_handler

    # @property
    # def seed_code(self):
    #     return self.seed.code
