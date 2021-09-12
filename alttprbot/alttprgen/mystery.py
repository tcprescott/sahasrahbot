import os

import aiofiles
import yaml
from aiohttp.client_exceptions import ClientResponseError
from tenacity import RetryError, AsyncRetrying, stop_after_attempt, retry_if_exception_type

import pyz3r
from alttprbot import models
from alttprbot.alttprgen.preset import fetch_preset
from alttprbot.alttprgen.randomizer import mysterydoors
from alttprbot.database import config
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.util.alttpr_discord import ALTTPRDiscord
from alttprbot_discord.util.alttprdoors_discord import AlttprDoorDiscord


class WeightsetNotFoundException(SahasrahBotException):
    pass

async def generate_test_game(weightset='weighted', festive=False):
    weights = await get_weights(weightset)

    mystery = mysterydoors.generate_doors_mystery(weights=weights)

    return mystery.settings


async def get_weights(weightset='weighted'):
    basename = os.path.basename(f'{weightset}.yaml')

    try:
        async with aiofiles.open(os.path.join("weights", basename)) as f:
            weights = yaml.safe_load(await f.read())
    except FileNotFoundError as err:
        raise WeightsetNotFoundException(
            f'Could not find weightset {weightset}.  See a list of available weights at https://sahasrahbot.synack.live/mystery.html') from err

    return weights


async def generate_random_game(weightset='weighted', weights=None, tournament=True, spoilers="off"):
    if weights is None:
        weights = await get_weights(weightset)

    try:
        async for attempt in AsyncRetrying(stop=stop_after_attempt(5), retry=retry_if_exception_type(ClientResponseError)):
            with attempt:
                try:
                    mystery = await generate(weights, spoilers=spoilers)

                    if mystery.doors:
                        seed = await AlttprDoorDiscord.create(
                            settings=mystery.settings,
                            spoilers=spoilers != "mystery",
                        )
                    else:
                        if mystery.customizer:
                            endpoint = "/api/customizer"
                        else:
                            endpoint = "/api/randomizer"

                        mystery.settings['tournament'] = tournament
                        mystery.settings['allow_quickswap'] = True
                        seed = await ALTTPRDiscord.generate(settings=mystery.settings, endpoint=endpoint)
                except ClientResponseError:
                    await models.AuditGeneratedGames.create(
                        randomizer='alttpr',
                        settings=mystery.settings,
                        gentype='mystery failure',
                        genoption=weightset,
                        customizer=1 if mystery.customizer else 0
                    )
                    raise
    except RetryError as e:
        raise e.last_attempt._exception from e

    await models.AuditGeneratedGames.create(
        randomizer='alttpr',
        hash_id=seed.hash,
        permalink=seed.url,
        settings=mystery.settings,
        gentype='mystery',
        genoption=weightset,
        customizer=1 if mystery.customizer else 0
    )

    mystery.seed = seed
    return mystery


async def generate(weights, spoilers="mystery"):
    if 'preset' in weights:
        rolledpreset = pyz3r.mystery.get_random_option(weights['preset'])
        if rolledpreset == 'none':
            return mysterydoors.generate_doors_mystery(weights=weights, spoilers=spoilers) # pylint: disable=unbalanced-tuple-unpacking
        else:
            preset_dict = await fetch_preset(rolledpreset, randomizer='alttpr')
            settings = preset_dict['settings']
            customizer = preset_dict.get('customizer', False)
            doors = preset_dict.get('doors', False)
            settings.pop('name', None)
            settings.pop('notes', None)
            settings['spoilers'] = spoilers
            custom_instructions = pyz3r.mystery.get_random_option(weights.get('custom_instructions', None))

            return mysterydoors.AlttprMystery(
                weights=weights,
                settings=settings,
                customizer=customizer,
                doors=doors,
                custom_instructions=custom_instructions
            )
    else:
        return mysterydoors.generate_doors_mystery(weights=weights, spoilers=spoilers) # pylint: disable=unbalanced-tuple-unpacking

