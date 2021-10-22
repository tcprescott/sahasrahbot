from alttprbot.alttprgen import generator
from alttprbot.exceptions import SahasrahBotException


class PresetNotFoundException(SahasrahBotException):
    pass


async def get_preset(preset, hints=False, nohints=False, spoilers="off", tournament=True, randomizer='alttpr', allow_quickswap=False):
    preset_dict = await fetch_preset(preset, randomizer)
    seed = await generate_preset(preset_dict, preset=preset, hints=hints, nohints=nohints, spoilers=spoilers, tournament=tournament, allow_quickswap=allow_quickswap)
    return seed, preset_dict


async def fetch_preset(preset, randomizer='alttpr'):
    preset_class = generator.PRESET_CLASS_MAPPING[randomizer]
    data: generator.SahasrahBotPresetCore = preset_class(preset)
    await data.fetch()

    return data.preset_data


async def generate_preset(preset_dict, preset=None, hints=False, nohints=False, spoilers="off", tournament=True, allow_quickswap=False):
    randomizer = preset_dict.get('randomizer', 'alttpr')

    preset_class: generator.SahasrahBotPresetCore = generator.PRESET_CLASS_MAPPING[randomizer]
    data = await preset_class.custom_from_dict(preset_dict, preset_name=preset)

    if randomizer == 'alttpr':
        seed = await data.generate(hints=hints, nohints=nohints, spoilers=spoilers, tournament=tournament, allow_quickswap=allow_quickswap)
    elif randomizer in ['sm', 'smz3']:
        seed = await data.generate(tournament=tournament)
    else:
        seed = await data.generate()
    return seed
