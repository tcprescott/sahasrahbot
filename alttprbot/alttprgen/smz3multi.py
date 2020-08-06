import pyz3r
from alttprbot.alttprgen.preset import fetch_preset
from alttprbot.exceptions import SahasrahBotException


class PresetNotFoundException(SahasrahBotException):
    pass

async def generate_multiworld(preset, players, tournament=False, randomizer='smz3'):
    preset_dict = await fetch_preset(preset, randomizer=randomizer)

    settings = preset_dict['settings']

    settings['race'] = "true" if tournament else "false"
    settings['gamemode'] = "multiworld"
    settings['players'] = len(players)
    for idx, player in enumerate(players):
        settings[f'player-{idx}'] = player

    seed = await pyz3r.sm(
        randomizer=randomizer,
        settings=settings
    )
    return seed
