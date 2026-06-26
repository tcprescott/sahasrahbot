"""Seed wrapper classes (Tier 2 — business).

These subclass the underlying randomizer clients (pyz3r / ``seedgen.randomizer``)
to add SahasrahBot's generation config (API base URL / auth) and the
``generated_goal`` settings summary. They contain **no presentation concerns** —
Discord embed rendering lives in
``alttprbot/presentation/discord/util/seed_embeds.py`` and dispatches on these
types. The generator and tournament code construct/return these classes; the
Discord layer renders them.
"""

import aiohttp
from pyz3r import ALTTPR
from pyz3r.sm import smClass

import config
from alttprbot.services.seedgen.randomizer.alttprdoor import AlttprDoor
from alttprbot.services.seedgen.randomizer.avianart import AVIANART


def is_enemizer(settings):
    return settings['enemizer.boss_shuffle'] != 'none' or settings['enemizer.enemy_shuffle'] != 'none' or settings[
        'enemizer.enemy_damage'] != 'default' or settings['enemizer.enemy_health'] != 'default'


class ALTTPRSeed(ALTTPR):
    def __init__(self, *args, **kwargs):
        super(ALTTPRSeed, self).__init__(*args, **kwargs)
        if 'baseurl' not in kwargs:
            self.baseurl = config.ALTTPR_BASEURL
        username = config.ALTTPR_USERNAME
        password = config.ALTTPR_PASSWORD
        self.auth = aiohttp.BasicAuth(login=username, password=password) if username and password else None

    @property
    def generated_goal(self):
        settings_list = []
        meta = self.data['spoiler'].get('meta', {})

        if meta.get('spoilers', 'off') == 'mystery':
            return 'mystery'

        settings = {
            'mode': meta.get('mode', 'open'),
            'weapons': meta.get('weapons', 'randomized'),
            'goal': meta.get('goal', 'ganon'),
            'logic': meta.get('logic', 'NoGlitches'),
            'shuffle': meta.get('shuffle', 'none'),
            'item_pool': meta.get('item_pool', 'normal'),
            'dungeon_items': meta.get('dungeon_items', 'standard'),
            'item_functionality': meta.get('item_functionality', 'normal'),
            'entry_crystals_ganon': meta.get('entry_crystals_ganon', '7'),
            'entry_crystals_tower': meta.get('entry_crystals_tower', '7'),
            'enemizer.boss_shuffle': meta.get('enemizer.boss_shuffle', 'none'),
            'enemizer.enemy_damage': meta.get('enemizer.enemy_damage', 'default'),
            'enemizer.enemy_health': meta.get('enemizer.enemy_health', 'default'),
            'enemizer.enemy_shuffle': meta.get('enemizer.enemy_shuffle', 'none'),
        }

        if not settings['item_pool'] in ['easy', 'normal'] or not settings['item_functionality'] in ['easy', 'normal']:
            settings_list.append('hard')
        elif settings['dungeon_items'] == 'full' and not settings['goal'] == 'dungeons':
            settings_list.append('normal')

        if is_enemizer(settings):
            settings_list.append("enemizer")

        if settings['weapons'] == 'swordless':
            settings_list.append('swordless')

        if not (settings['dungeon_items'] == 'full' and settings['goal'] == 'dungeons'):
            if settings['mode'] == 'open':
                if settings['shuffle'] == 'none' and not is_enemizer(settings) and (
                        settings['item_pool'] == 'normal' and settings['item_functionality'] == 'normal') and not \
                settings['weapons'] == 'swordless':
                    settings_list.append('casual')
                settings_list.append('open')
            elif settings['mode'] == 'standard' and settings['weapons'] == 'randomized':
                settings_list.append('standard')
            elif settings['mode'] == 'standard' and settings['weapons'] == 'assured' and (
                    settings['item_pool'] == 'normal' and settings['item_functionality'] == 'normal'):
                settings_list.append('casual')
            elif settings['mode'] == 'inverted':
                settings_list.append('inverted')
            elif settings['mode'] == 'retro':
                settings_list.append('retro')

        if settings['goal'] == 'OverworldGlitches':
            settings_list.append("overworld glitches")
        elif settings['goal'] == 'MajorGlitches':
            settings_list.append("major glitches")
        elif settings['goal'] == 'NoLogic':
            settings_list.append("no logic")

        if not settings['entry_crystals_tower'] == '7' or not settings['entry_crystals_ganon'] == '7':
            settings_list.append(
                f"{settings['entry_crystals_tower']}/{settings['entry_crystals_ganon']}")

        if settings['goal'] == 'ganon' and settings['shuffle'] != 'none':
            settings_list.append("defeat ganon")
        elif settings['goal'] == 'fast_ganon' and settings['shuffle'] == 'none':
            settings_list.append("fast ganon")
        elif settings['goal'] == 'dungeons':
            settings_list.append("all dungeons")
        elif settings['goal'] == 'triforce-hunt':
            settings_list.append("triforce hunt")
        elif settings['goal'] == 'pedestal':
            settings_list.append("pedestal")

        if settings['dungeon_items'] == 'mc':
            settings_list.append("mc")
        elif settings['dungeon_items'] == 'mcs':
            settings_list.append("mcs")
        elif settings['dungeon_items'] == 'full':
            settings_list.append("keysanity")

        if not settings['shuffle'] == 'none':
            settings_list.append("+ entrance shuffle")

        if meta.get('difficulty', None) == 'custom':
            settings_list.append("(customizer)")

        return " ".join(settings_list)


class AlttprDoorSeed(AlttprDoor):
    def __init__(self, *args, **kwargs):
        super(AlttprDoorSeed, self).__init__(*args, **kwargs)

    @property
    def generated_goal(self):
        return "door randomizer"


class AVIANARTSeed(AVIANART):
    def __init__(self, *args, **kwargs):
        super(AVIANARTSeed, self).__init__(*args, **kwargs)

    @property
    def generated_goal(self):
        return self.preset


class SMSeed(smClass):
    def __init__(self, *args, **kwargs):
        super(SMSeed, self).__init__(*args, **kwargs)
        self.randomizer = 'sm'

    @property
    def generated_goal(self):
        return self.randomizer


class SMZ3Seed(SMSeed):
    def __init__(self, *args, **kwargs):
        super(SMZ3Seed, self).__init__(*args, **kwargs)
        self.randomizer = 'smz3'
