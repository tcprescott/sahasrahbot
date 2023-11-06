import copy
import logging
import random

import discord
from pyz3r.customizer import BASE_CUSTOMIZER_PAYLOAD
from werkzeug.datastructures import MultiDict

from alttprbot import models
from alttprbot.alttprgen.generator import ALTTPRPreset
from alttprbot.tournament.alttpr import ALTTPRTournamentRace
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot
from alttprbot_discord.util import alttpr_discord

ALTTPRDE_TITLE_MAP = {
    'Standard': 'standard',
    'Open': 'open',
    'Casual Boots': 'casualboots',
}

TRIFORCE_TEXTS = [
    'Motivation\n\nschlaegt\nErfahrung',
    'Lastlocation\nExtravaganza',
    'Lukas bring\nmir bitte ne\nWeinschorle!',
    'Und jetzt\nvanilla\nFusions!',
    'Escape is our\nPrison and we\nserve for life',
    'Last Location:\nTriforce\nEnde des Seeds',
    'Bruder\nmuss\nlos',
    'Und\njetzt\nDoors?',
    'Single Arrow\nist immer\nGoMode! - LwJ',
    'I WANNA BE THE\nGERMAN\nCHAMPION',
    'We think\nIce Trinexx\ncaught a cold',
    '\n  HOVERSEED!',
    '   THIS WAS\n   CLEARY A\n  SKILL ISSUE',
    'das haette man\nauch eher\nhaben koennen',
    'Sorry but your\nicerod is in\nanother seed',
    'Ich komm mit\nHookshoot\nwieder!!',
    'AND WHO\n   ARE YOU\n        AGAIN?',
    'SCHAUFEL\nder wichtigste\nCheck im Spiel',
    'You still need\nto draw the\nPedestal Lonk',
    'uff..\nQuality\nContent!',
    'Ich mache\nHelma immer\nmit Bomben.',
    '   THIS\n    IS\nRANDOOOOOOOO',
    'Der Berch\nRuuuuuuuuuuuft',
    'Hey, I wish a\ndamn fine cup\nof coffee!',
    'LSS LSS LSS\nLSS LSS LSS\nnein nein nein',
    'Doener\nmacht\nschoener',
    'Vault-Tech!\nPrepare for\nthe future!',
    'und jetzt\ngibts pizza\nfuer alle',
    'Stiefel\nSein\nMann',
]


class ALTTPRDETournamentGroups(ALTTPRTournamentRace):
    async def roll(self):
        try:
            preset = ALTTPRDE_TITLE_MAP[self.episode['match1']['title']]
        except KeyError:
            await self.rtgg_handler.send_message(
                "Invalid mode chosen, please contact a tournament admin for assistance.")
            raise
        self.seed = await ALTTPRPreset(preset).generate(hints=False, spoilers="off", allow_quickswap=True)

    async def configuration(self):
        guild = discordbot.get_guild(469300113290821632)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game',
            event_slug="alttprcd",
            audit_channel=discordbot.get_channel(473668481011679234),
            commentary_channel=discordbot.get_channel(469317757331308555),
            helper_roles=[
                guild.get_role(534030648713674765),
                guild.get_role(469300493542490112),
                guild.get_role(623071415129866240),
            ],
            lang='de',
            stream_delay=10,
            gsheet_id='1dWzbwxoErGQyO4K1tZ-EexX1bdnTGuxQhLJDnmfcaR4',
        )


class ALTTPRDETournamentBrackets(ALTTPRTournamentRace):
    async def roll(self):
        if self.bracket_settings is None:
            raise Exception('Missing bracket settings.  Please submit!')

        self.preset_dict = None
        settings = self.bracket_settings
        text = random.choice(TRIFORCE_TEXTS)
        print(text)
        settings['texts'] = {
            'end_triforce': "{NOBORDER}\n{SPEED6}\n" + text + "\n{PAUSE9}"
        }
        self.seed = await alttpr_discord.ALTTPRDiscord.generate(settings=settings, endpoint='/api/customizer')

    async def configuration(self):
        guild = discordbot.get_guild(469300113290821632)
        return TournamentConfig(
            guild=guild,
            racetime_category='alttpr',
            racetime_goal='Beat the game',
            event_slug="alttprcd",
            audit_channel=discordbot.get_channel(473668481011679234),
            commentary_channel=discordbot.get_channel(469317757331308555),
            helper_roles=[
                guild.get_role(534030648713674765),
                guild.get_role(469300493542490112),
                guild.get_role(623071415129866240),
            ],
            lang='de',
            stream_delay=10,
            gsheet_id='1dWzbwxoErGQyO4K1tZ-EexX1bdnTGuxQhLJDnmfcaR4',
            create_scheduled_events=True,
        )

    @property
    def bracket_settings(self):
        if self.tournament_game:
            return self.tournament_game.settings

        return None

    @property
    def submission_form(self):
        return "submission_alttprde.html"

    async def create_race_room(self):
        if self.tournament_game is None or self.tournament_game.settings is None:
            await self.send_race_submission_form(warning=True)
            raise Exception(f"Could not open `{self.episodeid}` because setttings were not submitted.")

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
            team_race=self.data.coop,
        )
        return self.rtgg_handler

    async def process_submission_form(self, payload: MultiDict, submitted_by: str):
        embed = discord.Embed(
            title=f"ALTTPR DE - {self.versus}",
            description='Thank you for submitting your settings for this race!  Below is what will be played.\nIf this is incorrect, please contact a tournament admin.',
            color=discord.Colour.blue()
        )

        embed.add_field(name="Episode ID", value=self.episodeid, inline=False)
        embed.add_field(name="Event", value=self.event_slug, inline=False)
        embed.add_field(name="Game #", value=payload['game'], inline=False)

        try:
            game_number = int(payload['game'])
        except ValueError:
            raise Exception("Invalid game number.")

        if game_number in [1, 2]:
            if payload['pool_2'] == 'german_hard':
                preset = await ALTTPRPreset('derduden2/german_hard').fetch()
                settings = copy.deepcopy(preset.preset_data['settings'])
            else:
                settings = copy.deepcopy(BASE_CUSTOMIZER_PAYLOAD)
            settings = apply_pool(settings, payload['pool_1'], payload['pool_2'], payload['pool_3'])
        elif game_number == 3:
            preset = await ALTTPRPreset('derduden2/german_hard').fetch()
            settings = copy.deepcopy(preset.preset_data['settings'])
        else:
            raise Exception("Invalid game number.")

        payload_formatted = '\n'.join(
            [f"**{key}**: {val}" for key, val in payload.items() if not key in ['episodeid', 'game']])
        embed.add_field(name="Settings", value=payload_formatted, inline=False)

        settings['name'] = f"ALTTPRDE - {self.versus} - Game {payload['game']}"
        settings['notes'] = f"Episode {self.episodeid}<br><br>{self.versus}<br>Game {payload['game']}"

        settings['hints'] = 'off'
        settings['tournament'] = True
        settings['spoilers'] = 'off'
        settings['allow_quickswap'] = True

        embed.add_field(name="Submitted by", value=submitted_by, inline=False)

        await models.TournamentGames.update_or_create(episode_id=self.episodeid,
                                                      defaults={'settings': settings, 'event': self.event_slug,
                                                                'game_number': payload['game']})

        if self.audit_channel:
            await self.audit_channel.send(embed=embed)

        for name, player in self.player_discords:
            if player is None:
                logging.error(f"Could not send DM to {name}")
                if self.audit_channel:
                    await self.audit_channel.send(f"@here could not send DM to {name}",
                                                  allowed_mentions=discord.AllowedMentions(everyone=True), embed=embed)
                continue
            try:
                await player.send(embed=embed)
            except discord.HTTPException:
                logging.exception(f"Could not send DM to {name}")
                if self.audit_channel:
                    await self.audit_channel.send(f"@here could not send DM to {player.name}#{player.discriminator}",
                                                  allowed_mentions=discord.AllowedMentions(everyone=True), embed=embed)


def apply_pool(settings, pool1, pool2, pool3):
    if pool1 == 'dungeons' and pool2 == 'fast_ganon':
        raise Exception("You cannot have all dungeons and fast ganon at the same time.")
    if pool1 == 'inverted' and pool2 == 'standard':
        raise Exception("You cannot have inverted and standard at the same time.")
    if pool1 == 'keysanity' and pool2 == 'mcs':
        raise Exception("You cannot have keysanity and MC Shuffle at the same time.")
    if pool1 == 'keysanity' and pool2 == 'bks':
        raise Exception("You cannot have keysanity and BK Shuffle at the same time.")

    if pool1 == 'enemy_shuffle' and pool2 == 'standard' and not pool3 == 'start_sword':
        raise Exception("You cannot have enemy shuffle and standard without starting with a sword.")

    settings['custom']['customPrizePacks'] = False

    # pool 1
    if pool1 == 'keysanity':
        settings['custom']['region.wildBigKeys'] = True
        settings['custom']['region.wildCompasses'] = True
        settings['custom']['region.wildKeys'] = True
        settings['custom']['region.wildMaps'] = True

        settings['custom']['rom.freeItemMenu'] = True
        settings['custom']['rom.freeItemText'] = True

        settings['custom']['rom.mapOnPickup'] = True
    elif pool1 == 'enemy_shuffle':
        settings['enemizer']['enemy_shuffle'] = 'shuffled'
    elif pool1 == 'inverted':
        settings['mode'] = 'inverted'
    elif pool1 == '66crystals':
        settings['crystals']['tower'] = 6
        settings['crystals']['ganon'] = 6
    elif pool1 == 'dungeons':
        settings['goal'] = 'dungeons'
    elif pool1 == 'miniswordless':
        settings['weapons'] = 'swordless'
        settings['l']['R2Fub24ncyBUb3dlciAtIE1vbGRvcm0gQ2hlc3Q6MQ=='] = 'SilverArrowUpgrade:1'

    # pool 2
    if pool2 == 'mcs':
        settings['custom']['region.wildCompasses'] = True
        settings['custom']['region.wildMaps'] = True

        settings['custom']['rom.freeItemMenu'] = True
        settings['custom']['rom.freeItemText'] = True

        settings['custom']['rom.mapOnPickup'] = True
    elif pool2 == 'bks':
        settings['custom']['region.wildBigKeys'] = True
        settings['custom']['rom.freeItemMenu'] = True
        settings['custom']['rom.freeItemText'] = True
    elif pool2 == 'standard':
        settings['mode'] = 'standard'
    elif pool2 == 'universal_keys':
        settings['custom']['rom.genericKeys'] = True
        settings['custom']['region.wildKeys'] = True
    elif pool2 == 'boss_shuffle':
        settings['enemizer']['boss_shuffle'] = 'full'
    elif pool2 == 'fast_ganon':
        settings['goal'] = 'fast_ganon'

    # pool 3
    if pool3 == 'start_sword':
        if settings['weapons'] == 'swordless':
            raise Exception("Cannot have swordless and start with sword.")
        settings['eq'].append('ProgressiveSword')
        settings['custom']['item']['count']['ProgressiveSword'] = max(
            settings['custom']['item']['count']['ProgressiveSword'] - 1, 0)
        settings['custom']['item']['count']['TwentyRupees'] += 1
    elif pool3 == 'start_boots':
        settings['eq'].append('PegasusBoots')
        settings['custom']['item']['count']['PegasusBoots'] = max(
            settings['custom']['item']['count']['PegasusBoots'] - 1, 0)
        settings['custom']['item']['count']['TwentyRupees'] += 1
    elif pool3 == 'start_flute':
        settings['eq'].append('OcarinaInactive' if settings['mode'] == 'standard' else 'OcarinaActive')
        settings['custom']['item']['count']['OcarinaInactive'] = max(
            settings['custom']['item']['count']['OcarinaInactive'] - 1, 0)
        settings['custom']['item']['count']['TwentyRupees'] += 1
    elif pool3 == 'start_bombs':
        settings['eq'].append('TenBombs')
    elif pool3 == 'start_rupees':
        settings['eq'].append('ThreeHundredRupees')

    return settings


def get_embed_field(name: str, embed: discord.Embed) -> str:
    for field in embed.fields:
        if field.name == name:
            return field.value
    return None
