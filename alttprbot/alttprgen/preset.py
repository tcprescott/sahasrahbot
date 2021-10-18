from dataclasses import dataclass
import os
import random

import aiofiles
import yaml

from alttprbot import models
from alttprbot.alttprgen.randomizer import ctjets
from alttprbot.database import config
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.util.alttpr_discord import ALTTPRDiscord
from alttprbot_discord.util.alttprdoors_discord import AlttprDoorDiscord
from alttprbot_discord.util.sm_discord import SMDiscord, SMZ3Discord


class PresetNotFoundException(SahasrahBotException):
    pass


class AttemptToSaveGlobalPreset(SahasrahBotException):
    pass


class NamespaceNotFound(SahasrahBotException):
    pass


@dataclass
class PresetData:
    randomizer: str
    body: dict
    preset_name: str
    namespace: str = None


class SahasrahBotPresetCore():
    def __init__(self, randomizer: str, preset: str):
        self.randomizer = randomizer

        parsed = preset.split('/')
        if len(parsed) == 1:
            # we have a global preset
            self.namespace = None
            self.preset = parsed
        else:
            self.namespace = parsed[0]
            self.preset = parsed[1]

    async def fetch(self) -> PresetData:
        if self.namespace is None:
            await self.fetch_global()
        else:
            await self.fetch_namespaced()

        await self.post_processing()

        return self.data

    async def save(self, body) -> None:
        if self.namespace is None:
            raise AttemptToSaveGlobalPreset("You cannot save a global preset.")

        namespace_data = await models.PresetNamespaces.get(name=self.namespace)

        await models.Presets.update_or_create(preset_name=self.preset, namespace=namespace_data, defaults={'content': body})

    async def fetch_global(self):
        basename = os.path.basename(f'{self.preset}.yaml')
        try:
            async with aiofiles.open(os.path.join(f"presets/{self.randomizer}", basename)) as f:
                preset_dict = yaml.safe_load(await f.read())
        except FileNotFoundError as err:
            raise PresetNotFoundException(
                f'Could not find preset {self.preset}.  See a list of available presets at https://sahasrahbot.synack.live/presets.html') from err

        self.data = PresetData(
            randomizer=self.randomizer,
            body=preset_dict,
            preset_name=self.preset
        )

    async def fetch_namespaced(self):
        data = await models.Presets.get_or_none(preset_name=self.preset, namespace__name=self.namespace)

        if data is None:
            raise PresetNotFoundException(f'Could not find preset {self.preset} in namespace {self.namespace}.')

        self.data = PresetData(
            randomizer=self.randomizer,
            body=data.content,
            preset_name=self.preset,
            namespace=self.namespace
        )

    async def post_processing(self):
        return


class ALTTPRPreset(SahasrahBotPresetCore):
    def __init__(self, preset: str):
        super().__init__('alttpr', preset)

    async def post_processing(self):
        if self.data.body.get('customizer', False) and not self.data.body.get('doors', False):
            if 'l' not in self.data.body['settings']:
                self.data.body['settings']['l'] = {}
            for i in self.data.body.get('forced_locations', {}):
                location = random.choice([l for l in i['locations'] if l not in self.data.body['settings']['l']])
                self.data.body['settings']['l'][location] = i['item']

    async def generate(self, hints=False, nohints=False, spoilers="off", tournament=True, allow_quickswap=False):
        settings = self.data.body['settings']
        if self.data.body.get('doors', False):
            if hints:
                settings['hints'] = 'on'
            elif nohints:
                settings['hints'] = 'off'

            if allow_quickswap:
                settings['quickswap'] = True

            seed = await AlttprDoorDiscord.create(
                settings=settings,
                spoilers=spoilers == "on"
            )
            hash_id = seed.hash
        else:
            if hints:
                settings['hints'] = 'on'
            elif nohints:
                settings['hints'] = 'off'

            settings['tournament'] = tournament
            settings['spoilers'] = spoilers

            if not 'allow_quickswap' in settings:
                settings['allow_quickswap'] = allow_quickswap

            if self.data.body.get('customizer', False):
                endpoint = "/api/customizer"
            elif self.data.body.get('festive', False):
                endpoint = "/api/festive"
            else:
                endpoint = "/api/randomizer"

            seed = await ALTTPRDiscord.generate(
                settings=settings,
                endpoint=endpoint
            )
            hash_id = seed.hash

        await models.AuditGeneratedGames.create(
            randomizer=self.randomizer,
            hash_id=hash_id,
            permalink=seed.url,
            settings=settings,
            gentype='preset',
            genoption=self.preset,
            customizer=1 if self.data.body.get('customizer', False) else 0
        )
        return seed


class SMPreset(SahasrahBotPresetCore):
    def __init__(self, preset: str):
        super().__init__('sm', preset)

    async def generate(self, tournament=True):
        settings = self.data.body['settings']
        settings['race'] = "true" if tournament else "false"
        seed = await SMDiscord.create(
            settings=settings,
        )
        hash_id = seed.slug_id

        await models.AuditGeneratedGames.create(
            randomizer=self.randomizer,
            hash_id=hash_id,
            permalink=seed.url,
            settings=settings,
            gentype='preset',
            genoption=self.preset,
            customizer=0
        )
        return seed


class SMZ3Preset(SahasrahBotPresetCore):
    def __init__(self, preset: str):
        super().__init__('smz3', preset)

    async def generate(self, tournament=True):
        settings = self.data.body['settings']
        settings['race'] = "true" if tournament else "false"
        seed = await SMZ3Discord.create(
            settings=settings,
        )
        hash_id = seed.slug_id

        await models.AuditGeneratedGames.create(
            randomizer=self.randomizer,
            hash_id=hash_id,
            permalink=seed.url,
            settings=settings,
            gentype='preset',
            genoption=self.preset,
            customizer=0
        )
        return seed


class CTJetsPreset(SahasrahBotPresetCore):
    def __init__(self, preset: str):
        super().__init__('ctjets', preset)

    async def generate(self):
        settings = self.data.body['settings']
        seed_uri = await ctjets.roll_ctjets(settings, version=self.data.body.get('version', '3.1.0'))

        await models.AuditGeneratedGames.create(
            randomizer=self.randomizer,
            hash_id=None,
            permalink=seed_uri,
            settings=settings,
            gentype='preset',
            genoption=self.preset,
            customizer=0
        )
        return seed_uri


async def get_preset(preset, hints=False, nohints=False, spoilers="off", tournament=True, randomizer='alttpr', allow_quickswap=False):
    preset_dict = await fetch_preset(preset, randomizer)
    seed = await generate_preset(preset_dict, preset=preset, hints=hints, nohints=nohints, spoilers=spoilers, tournament=tournament, allow_quickswap=allow_quickswap)
    return seed, preset_dict


async def fetch_preset(preset, randomizer='alttpr'):
    preset = preset.lower()

    # make sure someone isn't trying some path traversal shennaniganons
    basename = os.path.basename(f'{preset}.yaml')

    try:
        async with aiofiles.open(os.path.join(f"presets/{randomizer}", basename)) as f:
            preset_dict = yaml.safe_load(await f.read())
        if preset_dict.get('festive') and not await config.get(0, 'FestiveMode') == "true":
            raise PresetNotFoundException(f'Could not find preset {preset}.  See a list of available presets at https://sahasrahbot.synack.live/presets.html')
    except FileNotFoundError as err:
        raise PresetNotFoundException(
            f'Could not find preset {preset}.  See a list of available presets at https://sahasrahbot.synack.live/presets.html') from err

    if preset_dict.get('customizer', False) and preset_dict.get('randomizer', 'alttpr') and not preset_dict.get('doors', False):
        if 'l' not in preset_dict['settings']:
            preset_dict['settings']['l'] = {}
        for i in preset_dict.get('forced_locations', {}):
            location = random.choice([l for l in i['locations'] if l not in preset_dict['settings']['l']])
            preset_dict['settings']['l'][location] = i['item']

    return preset_dict


async def generate_preset(preset_dict, preset=None, hints=False, nohints=False, spoilers="off", tournament=True, allow_quickswap=False):
    randomizer = preset_dict.get('randomizer', 'alttpr')
    settings = preset_dict['settings']

    if randomizer == 'alttpr':
        if preset_dict.get('doors', False):
            if hints:
                settings['hints'] = 'on'
            elif nohints:
                settings['hints'] = 'off'

            if allow_quickswap:
                settings['quickswap'] = True

            seed = await AlttprDoorDiscord.create(
                settings=settings,
                spoilers=spoilers == "on"
            )
            hash_id = seed.hash
        else:
            if hints:
                settings['hints'] = 'on'
            elif nohints:
                settings['hints'] = 'off'

            settings['tournament'] = tournament
            settings['spoilers'] = spoilers

            if not 'allow_quickswap' in settings:
                settings['allow_quickswap'] = allow_quickswap

            if preset_dict.get('customizer', False):
                endpoint = "/api/customizer"
            elif preset_dict.get('festive', False):
                endpoint = "/api/festive"
            else:
                endpoint = "/api/randomizer"

            seed = await ALTTPRDiscord.generate(
                settings=settings,
                endpoint=endpoint
            )
            hash_id = seed.hash

    # elif randomizer == 'alttprdoors':

    elif randomizer in ['sm']:
        settings['race'] = "true" if tournament else "false"
        seed = await SMDiscord.create(
            settings=settings,
        )
        hash_id = seed.slug_id

    elif randomizer in ['smz3']:
        settings['race'] = "true" if tournament else "false"
        seed = await SMZ3Discord.create(
            settings=settings,
        )
        hash_id = seed.slug_id

    else:
        raise SahasrahBotException(f'Randomizer {randomizer} is not supported.')

    await models.AuditGeneratedGames.create(
        randomizer=randomizer,
        hash_id=hash_id,
        permalink=seed.url,
        settings=settings,
        gentype='preset',
        genoption=preset,
        customizer=1 if preset_dict.get('customizer', False) else 0
    )
    return seed
