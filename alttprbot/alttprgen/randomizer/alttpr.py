"""ALTTPR (alttpr.com) API client.

Pure seed-generation code: no Discord or racetime imports. Discord embeds for
these seeds are built in ``alttprbot_discord/util/seed_embeds.py``.
"""
import aiohttp
from pyz3r import ALTTPR

import config


class ALTTPRClient(ALTTPR):
    """pyz3r's ALTTPR client, pointed at our configured base URL and credentials."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'baseurl' not in kwargs:
            self.baseurl = config.ALTTPR_BASEURL
        username = config.ALTTPR_USERNAME
        password = config.ALTTPR_PASSWORD
        self.auth = aiohttp.BasicAuth(login=username, password=password) if username and password else None

    @property
    def generated_goal(self):
        return generated_goal(self.data)


ENEMY_SHUFFLE = 'enemizer.enemy_shuffle'
BOSS_SHUFFLE = 'enemizer.boss_shuffle'
ENEMY_DAMAGE = 'enemizer.enemy_damage'
ENEMY_HEALTH = 'enemizer.enemy_health'

GLITCH_WORDS = {
    'OverworldGlitches': "overworld glitches",
    'MajorGlitches': "major glitches",
    'NoLogic': "no logic",
}

DUNGEON_ITEM_WORDS = {
    'mc': "mc",
    'mcs': "mcs",
    'full': "keysanity",
}


def is_enemizer(settings):
    return settings[BOSS_SHUFFLE] != 'none' or settings[ENEMY_SHUFFLE] != 'none' or settings[
        ENEMY_DAMAGE] != 'default' or settings[ENEMY_HEALTH] != 'default'


def _is_normal_pool(settings):
    return settings['item_pool'] == 'normal' and settings['item_functionality'] == 'normal'


def _difficulty_word(settings):
    if settings['item_pool'] not in ['easy', 'normal'] or settings['item_functionality'] not in ['easy', 'normal']:
        return 'hard'
    if settings['dungeon_items'] == 'full' and settings['goal'] != 'dungeons':
        return 'normal'
    return None


def _mode_words(settings):
    if settings['dungeon_items'] == 'full' and settings['goal'] == 'dungeons':
        return []
    mode, weapons = settings['mode'], settings['weapons']
    if mode == 'open':
        casual = (settings['shuffle'] == 'none' and not is_enemizer(settings) and _is_normal_pool(settings)
                  and weapons != 'swordless')
        return ['casual', 'open'] if casual else ['open']
    if mode == 'standard' and weapons == 'randomized':
        return ['standard']
    if mode == 'standard' and weapons == 'assured' and _is_normal_pool(settings):
        return ['casual']
    if mode in ('inverted', 'retro'):
        return [mode]
    return []


def _goal_word(settings):
    goal, shuffled = settings['goal'], settings['shuffle'] != 'none'
    if goal == 'ganon' and shuffled:
        return "defeat ganon"
    if goal == 'fast_ganon' and not shuffled:
        return "fast ganon"
    return {'dungeons': "all dungeons", 'triforce-hunt': "triforce hunt", 'pedestal': "pedestal"}.get(goal)


def generated_goal(data):
    """Describe a generated ALTTPR game (e.g. "casual open") from its API response data."""
    meta = data['spoiler'].get('meta', {})

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
        BOSS_SHUFFLE: meta.get(BOSS_SHUFFLE, 'none'),
        ENEMY_DAMAGE: meta.get(ENEMY_DAMAGE, 'default'),
        ENEMY_HEALTH: meta.get(ENEMY_HEALTH, 'default'),
        ENEMY_SHUFFLE: meta.get(ENEMY_SHUFFLE, 'none'),
    }

    settings_list = [
        _difficulty_word(settings),
        "enemizer" if is_enemizer(settings) else None,
        'swordless' if settings['weapons'] == 'swordless' else None,
        *_mode_words(settings),
        # The glitch level is read from 'goal', as it always has been.
        GLITCH_WORDS.get(settings['goal']),
    ]

    if settings['entry_crystals_tower'] != '7' or settings['entry_crystals_ganon'] != '7':
        settings_list.append(f"{settings['entry_crystals_tower']}/{settings['entry_crystals_ganon']}")

    settings_list += [
        _goal_word(settings),
        DUNGEON_ITEM_WORDS.get(settings['dungeon_items']),
        "+ entrance shuffle" if settings['shuffle'] != 'none' else None,
        "(customizer)" if meta.get('difficulty', None) == 'custom' else None,
    ]

    return " ".join(word for word in settings_list if word)
