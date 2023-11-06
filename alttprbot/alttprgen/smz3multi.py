# import pyz3r
from alttprbot.alttprgen.preset import fetch_preset
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.util.sm_discord import SMDiscord, SMZ3Discord


class PresetNotFoundException(SahasrahBotException):
    pass


async def generate_multiworld(preset, players, tournament=False, randomizer='smz3', seed_number=None):
    preset_dict = await fetch_preset(preset, randomizer=randomizer)

    settings = preset_dict['settings']

    settings['race'] = "true" if tournament else "false"
    settings['gamemode'] = "multiworld"
    settings['players'] = len(players)

    if seed_number:
        settings['seed'] = str(seed_number)

    for idx, player in enumerate(players):
        settings[f'player-{idx}'] = player

    settings['race'] = "true" if tournament else "false"
    if randomizer == 'sm':
        seed = await SMDiscord.create(
            settings=settings,
        )
    elif randomizer == 'smz3':
        seed = await SMZ3Discord.create(
            settings=settings,
        )

    return seed
