from alttprbot.alttprgen import generator
from alttprbot.exceptions import SahasrahBotException
from alttprbot.alttprgen.randomizer.sm import SMClient, SMZ3Client


class PresetNotFoundException(SahasrahBotException):
    pass


async def generate_multiworld(preset, players, tournament=False, randomizer='smz3', seed_number=None):
    preset_data = generator.PRESET_CLASS_MAPPING[randomizer](preset)
    await preset_data.fetch()

    settings = preset_data.preset_data['settings']

    settings['race'] = "true" if tournament else "false"
    settings['gamemode'] = "multiworld"
    settings['players'] = len(players)

    if seed_number:
        settings['seed'] = str(seed_number)

    for idx, player in enumerate(players):
        settings[f'player-{idx}'] = player

    settings['race'] = "true" if tournament else "false"
    if randomizer == 'sm':
        seed = await SMClient.create(
            settings=settings,
            # The preset's own host (sm.samus.link for SM); pyz3r's default is samus.link (#63).
            baseurl=preset_data.baseurl,
        )
    elif randomizer == 'smz3':
        seed = await SMZ3Client.create(
            settings=settings,
            baseurl=preset_data.baseurl,
        )

    return seed
