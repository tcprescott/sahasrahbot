"""ALTTPR (alttpr.com) API client.

Pure seed-generation code: no Discord or racetime imports. Discord embeds for
these seeds are built in ``alttprbot_discord/util/seed_embeds.py``.
"""
import json
import logging

import aiohttp
from pyz3r import ALTTPR
from pyz3r.exceptions import AlttprFailedToGenerate

import config
from alttprbot.exceptions import InvalidInputError

logger = logging.getLogger(__name__)

# Longest alttpr.com error text passed on to the person (a Discord message holds 2000).
MAX_REJECTION_LENGTH = 1500


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

    async def generate_game(self, settings, endpoint):
        """pyz3r's generate_game, but a 4xx from alttpr.com is reported, not retried.

        pyz3r retries every failed request five times and then raises a bare "failed to
        generate game", so someone whose custom preset has a bad setting never learns which
        one (#65). alttpr.com answers bad settings with a 4xx whose body says what's wrong;
        that becomes an InvalidInputError carrying the message. Server errors and dropped
        connections are still retried.
        """
        self.settings = settings
        for _ in range(0, 5):
            try:
                async with aiohttp.request(method='post', url=self.uri(endpoint), json=settings, auth=self.auth) as resp:
                    if 400 <= resp.status < 500:
                        raise InvalidInputError(
                            f"alttpr.com could not generate this game: {rejection_reason(await resp.text())}")
                    resp.raise_for_status()
                    self.data = await resp.json()
                return self.data
            except (aiohttp.client_exceptions.ServerDisconnectedError, aiohttp.ClientResponseError):
                logger.warning("Unable to generate game, retrying.", exc_info=True)

        raise AlttprFailedToGenerate('failed to generate game')


def rejection_reason(body: str) -> str:
    """The readable part of an alttpr.com error response.

    Laravel's validation errors look like ``{"message": ..., "errors": {"field": ["..."]}}``;
    anything else is passed on as text.
    """
    reason = (_json_reason(body) or body).strip() or "no reason given"
    if len(reason) > MAX_REJECTION_LENGTH:
        reason = reason[:MAX_REJECTION_LENGTH] + "…"
    return reason


def _json_reason(body: str):
    try:
        data = json.loads(body)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    errors = data.get('errors')
    if isinstance(errors, dict) and errors:
        return '; '.join(f"{field}: {_joined(messages)}" for field, messages in errors.items())
    return str(data['message']) if data.get('message') else None


def _joined(messages):
    if isinstance(messages, list):
        return ' '.join(str(m) for m in messages)
    return messages


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
