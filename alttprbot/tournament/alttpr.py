import logging

import discord

from alttprbot.alttprgen import preset
from alttprbot import models
from alttprbot.tournaments import TOURNAMENT_DATA
from alttprbot.tournament.core import TournamentRace
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.bot import discordbot
from alttprbot_discord.util import alttpr_discord

SETTINGSMAP = {
    'Defeat Ganon': 'ganon',
    'Fast Ganon': 'fast_ganon',
    'All Dungeons': 'dungeons',
    'Pedestal': 'pedestal',
    'Standard': 'standard',
    'Open': 'open',
    'Inverted': 'inverted',
    'Retro': 'retro',
    'Randomized': 'randomized',
    'Assured': 'assured',
    'Vanilla': 'vanilla',
    'Swordless': 'swordless',
    'Shuffled': 'shuffled',
    'Full': 'full',
    'Random': 'random',
    'Hard': 'hard',
    'Normal': 'normal',
    'Off': 'off',
    'On': 'on',
    'None': 'none'
}

ALTTPR_FR_SETTINGS_LIST = [
    {
        'key': 'dungeon_items',
        'label': 'Dungeon Item Shuffle',
        'settings': {
            'standard': 'Standard',
            'mc': 'Maps and Compasses',
            'mcs': 'Maps, Compasses, and Small Keys',
            'full': 'Keysanity',
        }
    },
    {
        'key': 'goal',
        'label': 'Goal',
        'settings': {
            'ganon': 'Defeat Ganon',
            'fast_ganon': 'Fast Ganon',
        }
    },
    {
        'key': 'world_state',
        'label': 'World State',
        'settings': {
            'open': 'Open',
            'standard': 'Standard',
            'inverted': 'Inverted',
            'retro': 'Retro',
        }
    },
    {
        'key': 'boss_shuffle',
        'label': 'Boss Shuffle',
        'settings': {
            'none': 'Off',
            'random': 'Random'
        }
    },
    {
        'key': 'enemy_shuffle',
        'label': 'Enemy Shuffle',
        'settings': {
            'none': 'Off',
            'shuffled': 'Shuffled'
        }
    },
    {
        'key': 'hints',
        'label': 'Hints',
        'settings': {
            'off': 'Off',
            'on': 'On'
        }
    },
    {
        'key': 'swords',
        'label': 'Swords',
        'settings': {
            'randomized': 'Randomized',
            'assured': 'Assured',
            'vanilla': 'Vanilla',
            'swordless': 'Swordless',
        }
    },
    {
        'key': 'item_pool',
        'label': 'Item Pool',
        'settings': {
            'normal': 'Normal',
            'hard': 'Hard'
        }
    },
    {
        'key': 'item_functionality',
        'label': 'Item Functionality',
        'settings': {
            'normal': 'Normal',
            'hard': 'Hard'
        }
    },
]

ALTTPR_ES_SETTINGS_LIST = [
    {
        'key': 'preset',
        'label': 'Preset',
        'settings': {
            'ambrosia': 'Ambrosia',
            'casualboots': 'Casual Boots',
            'mcs': 'Maps, Compasses, and Small Keys',
            'open': 'Open',
            'standard': 'Standard',
            'adkeys': "All Dungeons + Keysanity (Round of 8 only)",
            'dungeons': 'All Dungeons (Round of 8 only)',
            'keysanity': 'Keysanity (Round of 8 only)',
        }
    }
]

class UnableToLookupUserException(SahasrahBotException):
    pass


class UnableToLookupEpisodeException(SahasrahBotException):
    pass

class ALTTPRTournamentRace(TournamentRace):
    async def roll(self):
        self.seed, self.preset_dict = await preset.get_preset('tournament', nohints=True, allow_quickswap=True)
        await self.create_embeds()

    # # handle rolling for alttprcd tournament (German)
    # async def roll_alttprcd(self):
    #     self.seed, self.preset_dict = await preset.get_preset('crossedkeydrop')

    # # handle rolling for francophone alttpr tournament
    # async def roll_alttprfr(self):
    #     if self.bracket_settings is None:
    #         raise Exception('Missing bracket settings.  Please submit!')

    #     self.preset_dict = None
    #     self.seed = await alttpr_discord.ALTTPRDiscord.generate(settings=self.bracket_settings)

    # async def roll_alttprhmg(self):
    #     self.seed, self.preset_dict = await preset.get_preset('hybridmg', allow_quickswap=True)

    # async def roll_alttpres(self):
    #     if self.bracket_settings is None:
    #         raise Exception('Missing bracket settings.  Please submit!')

    #     self.preset_dict = None
    #     self.seed = await alttpr_discord.ALTTPRDiscord.generate(
    #         settings=self.bracket_settings,
    #         endpoint='/api/customizer' if 'eq' in self.bracket_settings else '/api/randomizer',
    #     )

    # # test
    # async def roll_test(self):
    #     if self.bracket_settings is None:
    #         raise Exception('Missing bracket settings.  Please submit!')

    #     self.preset_dict = None
    #     self.seed = await alttpr_discord.ALTTPRDiscord.generate(
    #         settings=self.bracket_settings,
    #         endpoint='/api/customizer' if 'eq' in self.bracket_settings else '/api/randomizer',
    #     )

    # async def roll_smz3coop(self):
    #     self.seed, self.preset_dict = await preset.get_preset('hard', tournament=True, randomizer='smz3')

    # # handle rolling for alttpr main tournament
    # async def roll_alttpr(self):
    #     self.seed, self.preset_dict = await preset.get_preset('tournament', nohints=True, allow_quickswap=True)


    @property
    def seed_code(self):
        if isinstance(self.seed.code, list):
            return f"({'/'.join(self.seed.code)})"
        elif isinstance(self.seed.code, str):
            return f"({self.seed.code})"

        return ""

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

async def process_tournament_race(handler, episodeid=None):
    await handler.send_message("Generating game, please wait.  If nothing happens after a minute, contact Synack.")

    race = await models.TournamentResults.get_or_none(srl_id=handler.data.get('name'))
    if isinstance(handler.tournament, TournamentRace):
        tournament_race = handler.tournament
        await tournament_race.update_data()
    else:
        if race:
            episodeid = race.episode_id
        if race is None and episodeid is None:
            await handler.send_message("Please provide an SG episode ID.")
            return

        try:
            handler.tournament = await TournamentRace.construct(episodeid=episodeid, rtgg_handler=handler)
        except Exception as e:
            logging.exception("Problem creating tournament race.")
            await handler.send_message(f"Could not process tournament race: {str(e)}")
            return

    await tournament_race.roll()

    await handler.set_raceinfo(tournament_race.race_info_rolled, overwrite=True)

    await tournament_race.send_audit_message(tournament_race.embed)
    await tournament_race.send_commentary_message(tournament_race.tournament_embed)

    for name, player in tournament_race.player_discords:
        await tournament_race.send_player_message(name, player, tournament_race.embed)

    tournamentresults, created = await models.TournamentResults.update_or_create(srl_id=handler.data.get('name'), defaults={'episode_id': tournament_race.episodeid, 'event': tournament_race.event_slug, 'spoiler': None})
    tournamentresults.permalink = tournament_race.seed.url
    await tournamentresults.save()

    await handler.send_message("Seed has been generated, you should have received a DM in Discord.  Please contact a Tournament Moderator if you haven't received the DM.")
    handler.seed_rolled = True

async def alttprfr_process_settings_form(payload, submitted_by):
    episode_id = int(payload['episodeid'])
    adjusted_payload = payload.to_dict(flat=True)

    tournament_race = await TournamentRace.construct(episodeid=episode_id, rtgg_handler=None)

    embed = discord.Embed(
        title=f"ALTTPR FR - {tournament_race.versus}",
        description='Thank you for submitting your settings for this race!  Below is what will be played.\nIf this is incorrect, please contact a tournament admin.',
        color=discord.Colour.blue()
    )

    if adjusted_payload['enemy_shuffle'] != "none" and adjusted_payload['world_state'] == 'standard' and adjusted_payload['swords'] in ['randomized', 'swordless']:
        adjusted_payload['swords'] = 'assured'

    settings = {
        "glitches": "none",
        "item_placement": "advanced",
        "dungeon_items": adjusted_payload.get("dungeon_items", "standard"),
        "accessibility": "items",
        "goal": adjusted_payload.get("goal", "ganon"),
        "crystals": {
            "ganon": "7",
            "tower": "7"
        },
        "mode": adjusted_payload.get("world_state", "mode"),
        "entrances": "none",
        "hints": adjusted_payload.get("hints", "off"),
        "weapons": adjusted_payload.get("swords", "randomized"),
        "item": {
            "pool": adjusted_payload.get("item_pool", "normal"),
            "functionality": adjusted_payload.get("item_functionality", "normal"),
        },
        "tournament": True,
        "spoilers": "off",
        "lang": "en",
        "enemizer": {
            "boss_shuffle": adjusted_payload.get("boss_shuffle", "none"),
            "enemy_shuffle": adjusted_payload.get("enemy_shuffle", "none"),
            "enemy_damage": "default",
            "enemy_health": "default",
            "pot_shuffle": "off"
        },
        "allow_quickswap": True
    }

    settings_formatted = ""
    for setting in ALTTPR_FR_SETTINGS_LIST:
        settings_formatted += f"**{setting['label']}:** {setting['settings'][adjusted_payload.get(setting['key'])]}\n"

    embed.add_field(name="Settings", value=settings_formatted, inline=False)

    embed.add_field(name="Submitted by", value=submitted_by, inline=False)

    await models.TournamentGames.update_or_create(episode_id=episode_id, defaults={'settings': settings, 'event': 'alttprfr'})

    audit_channel_id = tournament_race.data.audit_channel_id
    if audit_channel_id is not None:
        audit_channel = discordbot.get_channel(audit_channel_id)
        await audit_channel.send(embed=embed)
    else:
        audit_channel = None

    for name, player in tournament_race.player_discords:
        if player is None:
            await audit_channel.send(f"@here could not send DM to {name}", allowed_mentions=discord.AllowedMentions(everyone=True), embed=embed)
            continue
        try:
            await player.send(embed=embed)
        except discord.HTTPException:
            if audit_channel is not None:
                await audit_channel.send(f"@here could not send DM to {player.name}#{player.discriminator}", allowed_mentions=discord.AllowedMentions(everyone=True), embed=embed)

    return tournament_race

async def alttpres_process_settings_form(payload, submitted_by):
    episode_id = int(payload['episodeid'])

    tournament_race = await TournamentRace.construct(episodeid=episode_id, rtgg_handler=None)

    embed = discord.Embed(
        title=f"ALTTPR ES - {tournament_race.versus}",
        description='Thank you for submitting your settings for this race!  Below is what will be played.\nIf this is incorrect, please contact a tournament admin.',
        color=discord.Colour.blue()
    )

    preset_dict = await preset.fetch_preset(payload['preset'])

    preset_dict['tournament'] = True
    preset_dict['allow_quickswap'] = True
    preset_dict['spoilers'] = 'off'

    embed.add_field(name="Preset", value=payload['preset'], inline=False)

    embed.add_field(name="Submitted by", value=submitted_by, inline=False)

    await models.TournamentGames.update_or_create(episode_id=episode_id, defaults={'settings': preset_dict['settings'], 'event': 'alttpres'})

    audit_channel_id = tournament_race.data.audit_channel_id
    if audit_channel_id is not None:
        audit_channel = discordbot.get_channel(audit_channel_id)
        await audit_channel.send(embed=embed)
    else:
        audit_channel = None

    for name, player in tournament_race.player_discords:
        if player is None:
            await audit_channel.send(f"@here could not send DM to {name}", allowed_mentions=discord.AllowedMentions(everyone=True), embed=embed)
            continue
        try:
            await player.send(embed=embed)
        except discord.HTTPException:
            if audit_channel is not None:
                await audit_channel.send(f"@here could not send DM to {player.name}#{player.discriminator}", allowed_mentions=discord.AllowedMentions(everyone=True), embed=embed)

    return tournament_race

async def send_race_submission_form(episodeid):
    tournament_race = await TournamentRace.construct(episodeid=episodeid, rtgg_handler=None)
    await tournament_race.send_race_submission_form()
