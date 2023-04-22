import logging
import random
from typing import List

import discord

from alttprbot import models
from alttprbot.alttprgen import generator
from alttprbot.exceptions import SahasrahBotException
from alttprbot.tournament.core import TournamentConfig, TournamentRace
from alttprbot.util import triforce_text
from alttprbot_discord.bot import discordbot


class ALTTPRTournamentRace(TournamentRace):
    """
    ALTTPTournamentRace represets a generic ALTTP tournament
    """
    async def roll(self):
        # self.seed, self.preset_dict = await preset.get_preset('tournament', nohints=True, allow_quickswap=True)
        pass

    async def process_tournament_race(self, args, message):
        await self.rtgg_handler.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")

        await self.update_data()
        await self.roll()
        await self.create_embeds()

        await self.rtgg_handler.set_bot_raceinfo(self.seed_code)

        await self.send_audit_message(embed=self.embed)
        await self.send_commentary_message(self.tournament_embed)

        for name, player in self.player_discords:
            await self.send_player_message(name, player, self.embed)

        tournamentresults, _ = await models.TournamentResults.update_or_create(srl_id=self.rtgg_handler.data.get('name'), defaults={'episode_id': self.episodeid, 'event': self.event_slug, 'spoiler': None})
        tournamentresults.permalink = self.seed.url
        await tournamentresults.save()

        await self.rtgg_handler.send_message("Seed has been generated, you should have received a DM in Discord.  Please contact a Tournament Moderator if you haven't received the DM.")
        self.rtgg_handler.seed_rolled = True

    async def send_room_welcome(self):
        await self.rtgg_handler.send_message('Welcome. Use !tournamentrace (without any arguments) to roll your seed!  This should be done about 5 minutes prior to the start of your race.  You do NOT need to wait for your setup helper to do this or start your race, they will appear later to setup the stream.')

    @property
    def seed_code(self):
        return f"({'/'.join(self.seed.code)})"

    @property
    def bracket_settings(self):
        return None

    async def create_embeds(self):
        if self.rtgg_handler is None:
            raise SahasrahBotException("No RaceTime.gg handler associated with this tournament game.")

        self.embed = await self.seed.embed(
            name=self.race_info,
            notes=self.versus,
            emojis=discordbot.emojis
        )

        self.tournament_embed = await self.seed.tournament_embed(
            name=self.race_info,
            notes=self.versus,
            emojis=discordbot.emojis
        )

        self.tournament_embed.insert_field_at(0, name='RaceTime.gg', value=self.rtgg_handler.bot.http_uri(self.rtgg_handler.data['url']), inline=False)
        self.embed.insert_field_at(0, name='RaceTime.gg', value=self.rtgg_handler.bot.http_uri(self.rtgg_handler.data['url']), inline=False)

        if self.broadcast_channels:
            self.tournament_embed.insert_field_at(0, name="Broadcast Channels", value=', '.join([f"[{a}](https://twitch.tv/{a})" for a in self.broadcast_channels]), inline=False)
            self.embed.insert_field_at(0, name="Broadcast Channels", value=', '.join([f"[{a}](https://twitch.tv/{a})" for a in self.broadcast_channels]), inline=False)

    async def send_race_submission_form(self, warning=False):
        if self.bracket_settings is not None and not warning:
            return

        if self.tournament_game and self.tournament_game.submitted and not warning:
            return

        if warning:
            msg = (
                f"Your upcoming race room cannot be created because settings have not submitted: `{self.versus}`!\n\n"
                f"For your convenience, please visit {self.submit_link} to submit the settings.\n\n"
            )
        else:
            msg = (
                f"Greetings!  Do not forget to submit settings for your upcoming race: `{self.versus}`!\n\n"
                f"For your convenience, please visit {self.submit_link} to submit the settings.\n\n"
            )

        for name, player in self.player_discords:
            if player is None:
                continue
            logging.info("Sending tournament submit reminder to %s.", name)
            await player.send(msg)

        await models.TournamentGames.update_or_create(episode_id=self.episodeid, defaults={'event': self.event_slug, 'submitted': 1})


class ALTTPR2023Race(ALTTPRTournamentRace):
    """
    ALTTPR2023Race is a class that represents the ALTTPR Main Tournament for the 2023 season.
    """
    async def roll(self):
        self.seed, self.preset, self.deck = await roll_seed([p[1] for p in self.player_discords], episode_id=self.episodeid)
        await self.rtgg_handler.send_message("-----------------")
        await self.rtgg_handler.send_message(f"Your preset is: {self.preset}")
        if self.deck:
            await self.rtgg_handler.send_message("-----------------")
            await self.rtgg_handler.send_message("Deck used to generate this game.")
            for preset, cards in self.deck.items():
                await self.rtgg_handler.send_message(f"{preset}: {cards}")
        await self.rtgg_handler.send_message("-----------------")

    @property
    def seed_code(self):
        return f"{self.preset} - ({'/'.join(self.seed.code)})"

    async def create_embeds(self):
        await super().create_embeds()
        self.embed.insert_field_at(0, name="Preset", value=self.preset, inline=False)
        if self.deck:
            self.embed.insert_field_at(1, name="Deck", value="\n".join([f"**{p}**: {c}" for p, c in self.deck.items()]), inline=False)

    async def configuration(self):
        guild = discordbot.get_guild(334795604918272012)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game',
            event_slug="alttpr",
            audit_channel=discordbot.get_channel(647966639266201620),
            commentary_channel=discordbot.get_channel(947095820673638400),
            scheduling_needs_channel=discordbot.get_channel(434560353461075969),
            scheduling_needs_tracker=True,
            create_scheduled_events=True,
            stream_delay=10,
            gsheet_id='1epZRDXfe-O4BBerzOEZbFMOVCFrVXU6TCDNjp66P7ZI',
            helper_roles=[
                guild.get_role(334797023054397450),
                guild.get_role(435200206552694794),
                guild.get_role(482353483853332481),
                guild.get_role(426487540829388805),
                guild.get_role(613394561594687499),
                guild.get_role(334796844750209024)
            ]
        )


async def roll_seed(players: List[discord.Member], episode_id: int = None, event_slug="alttpr2023"):
    """
    Roll a seed for the given players.
    """
    if not episode_id is None:
        existing_preset_for_episode = await models.TournamentPresetHistory.filter(episode_id=episode_id, event_slug=event_slug).first()
        if existing_preset_for_episode:
            seed = await generator.ALTTPRPreset(existing_preset_for_episode.preset).generate(allow_quickswap=True, tournament=True, hints=False, spoilers="off")
            return seed, existing_preset_for_episode.preset, None

    deck = {
        'tournament_hard': 2 * len(players),
        'standardboots': 2 * len(players),
        'invrosia': 2 * len(players),
        'fadkeys_gt': 2 * len(players),
        'tournament_mcboss': 2 * len(players),
    }
    for player in players:
        history = await models.TournamentPresetHistory.filter(discord_user_id=player.id, event_slug=event_slug).order_by('-timestamp').limit(5)
        if history:
            deck[history[0].preset] -= 1 if deck[history[0].preset] > 0 else 0

        for h in history:
            deck[h.preset] -= 1 if deck[h.preset] > 0 else 0

    preset = random.choices(list(deck.keys()), weights=list(deck.values()))[0]

    for player in players:
        await models.TournamentPresetHistory.create(discord_user_id=player.id, preset=preset, episode_id=episode_id, event_slug=event_slug)

    seed = await triforce_text.generate_with_triforce_text("alttpr2023", preset)
    return seed, preset, deck
