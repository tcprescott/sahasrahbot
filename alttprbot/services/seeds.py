"""Rolling seeds from presets, and looking up seeds SahasrahBot rolled, for the API
and the MCP server. The Discord commands roll through ``alttprbot/alttprgen/generator.py``
directly; this wraps the same calls and returns plain data.

A preset is named as the Discord commands name it: ``open`` for a built-in one, or
``namespace/name`` for someone's own.
"""

from dataclasses import dataclass
from typing import Optional

from alttprbot.alttprgen import generator
from alttprbot.exceptions import InvalidInputError, NotFoundError
from alttprbot.services import generated_games

RANDOMIZERS = ('alttpr', 'alttprmystery', 'sm', 'smz3')
ALTTPR_BRANCHES = ('live', 'beeta', 'tournament')


@dataclass(frozen=True)
class RollOptions:
    race: bool = False
    hints: bool = False
    allow_quickswap: bool = True
    branch: str = 'live'
    spoiler_race: bool = False


def _code(seed) -> Optional[list[str]]:
    try:
        code = seed.code
    except (AttributeError, KeyError, TypeError):
        return None
    return list(code) if code else None


def _hash(seed) -> Optional[str]:
    for attr in ('hash', 'hash_id', 'slug_id'):
        value = getattr(seed, attr, None)
        if value:
            return str(value)
    return None


def _rolled(randomizer: str, preset: str, seed, **extra) -> dict:
    return {
        'randomizer': randomizer,
        'preset': preset,
        'url': seed.url,
        'hash': _hash(seed),
        'file_select_code': _code(seed),
        'spoiler_url': None,
        'custom_instructions': None,
        **extra,
    }


async def roll(randomizer: str, preset: str, options: RollOptions = RollOptions()) -> dict:
    """Roll a seed from ``preset`` and return where it is.

    Raises ``NotFoundError`` for a preset that doesn't exist and ``InvalidInputError``
    for a randomizer or branch SahasrahBot can't roll."""
    if randomizer not in RANDOMIZERS:
        raise InvalidInputError(f"SahasrahBot can roll {', '.join(RANDOMIZERS)} seeds, not {randomizer}.")
    if options.branch not in ALTTPR_BRANCHES:
        raise InvalidInputError(f"The branch must be one of {', '.join(ALTTPR_BRANCHES)}.")
    if not preset:
        raise InvalidInputError('Name the preset to roll.')
    try:
        if randomizer == 'alttpr':
            seed = await generator.ALTTPRPreset(preset).generate(
                hints=options.hints,
                spoilers='off' if options.race else 'on',
                tournament=options.race,
                allow_quickswap=options.allow_quickswap,
                branch=options.branch,
            )
            if not seed:
                raise InvalidInputError('The randomizer could not generate that game.')
            return _rolled(randomizer, preset, seed)
        if randomizer == 'alttprmystery':
            mystery = await generator.ALTTPRMystery(preset).generate(
                spoilers='mystery', tournament=options.race, allow_quickswap=options.allow_quickswap)
            return _rolled(randomizer, preset, mystery.seed, custom_instructions=mystery.custom_instructions or None)
        rolled = generator.SMPreset(preset) if randomizer == 'sm' else generator.SMZ3Preset(preset)
        await rolled.generate(tournament=options.race, spoilers=randomizer == 'smz3' and options.spoiler_race)
        spoiler = rolled.spoiler_url() if randomizer == 'smz3' else None
        return _rolled(randomizer, preset, rolled.seed, spoiler_url=spoiler)
    except (generator.PresetNotFoundException, generator.NamespaceNotFound,
            generator.WeightsetNotFoundException) as e:
        raise NotFoundError(f"There's no {randomizer} preset called {preset}.") from e


async def lookup(hash_id: str) -> dict:
    """What SahasrahBot recorded about a seed it rolled, without its settings."""
    game = await generated_games.find_by_hash(hash_id)
    if game is None:
        raise NotFoundError(f"SahasrahBot didn't roll a seed with the hash {hash_id}.")
    return {
        'hash': game.hash_id,
        'randomizer': game.randomizer,
        'kind': game.gentype,
        'preset': game.genoption,
        'url': game.permalink,
        'rolled_at': game.timestamp,
    }
