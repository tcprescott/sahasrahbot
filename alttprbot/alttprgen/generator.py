from dataclasses import dataclass
import os
import random

import aiofiles
import yaml

from alttprbot import models
from alttprbot.alttprgen.randomizer import ctjets
# from alttprbot.database import config
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


class NoPresetSpecified(SahasrahBotException):
    pass


@dataclass
class PresetData:
    randomizer: str
    preset_name: str
    preset_data: dict
    namespace: str = None


class SahasrahBotPresetCore():
    randomizer = None

    def __init__(self, preset: str = None):
        self.namespace = None
        self.preset = None
        self.preset_data: dict = None

        if preset:
            parsed = preset.split('/')
            if len(parsed) == 1:
                # we have a global preset
                self.namespace = None
                self.preset = preset
            else:
                self.namespace = parsed[0]
                self.preset = parsed[1]

    @classmethod
    async def custom(cls, content, preset_name=None):
        preset = cls(preset_name)
        preset.preset_data = yaml.safe_load(content)

        return preset

    async def fetch(self) -> PresetData:
        if self.preset is None:
            raise NoPresetSpecified("No preset was specified.")

        if self.namespace is None:
            await self.__fetch_global()
        else:
            await self.__fetch_namespaced()

        return PresetData(
            randomizer=self.randomizer,
            preset_data=self.preset_data,
            preset_name=self.preset,
            namespace=self.namespace
        )

    async def save(self) -> None:
        if self.preset is None:
            raise NoPresetSpecified("No preset was specified.")

        if self.namespace is None:
            raise AttemptToSaveGlobalPreset("You cannot save a global preset.")

        body = yaml.dump(self.preset_data)
        namespace_data = await models.PresetNamespaces.get(name=self.namespace)

        await models.Presets.update_or_create(randomizer=self.randomizer, preset_name=self.preset, namespace=namespace_data, defaults={'content': body})

    async def __fetch_global(self):
        basename = os.path.basename(f'{self.preset}.yaml')
        try:
            async with aiofiles.open(os.path.join(f"presets/{self.randomizer}", basename)) as f:
                self.preset_data = yaml.safe_load(await f.read())
        except FileNotFoundError as err:
            raise PresetNotFoundException(
                f'Could not find preset {self.preset}.  See a list of available presets at https://sahasrahbot.synack.live/presets.html') from err

    async def __fetch_namespaced(self):
        data = await models.Presets.get_or_none(preset_name=self.preset, namespace__name=self.namespace)

        if data is None:
            raise PresetNotFoundException(f'Could not find preset {self.preset} in namespace {self.namespace}.')

        self.preset_data = yaml.safe_load(data.content)


class ALTTPRPreset(SahasrahBotPresetCore):
    randomizer = 'alttpr'

    async def generate(self, hints=False, nohints=False, spoilers="off", tournament=True, allow_quickswap=False):
        if self.preset_data is None:
            await self.fetch()

        settings = self.preset_data['settings']
        if self.preset_data.get('doors', False):
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
            if self.preset_data.get('customizer', False):
                if 'l' not in settings:
                    settings['l'] = {}
                for i in self.preset_data.get('forced_locations', {}):
                    location = random.choice([l for l in i['locations'] if l not in settings['l']])
                    settings['l'][location] = i['item']

            if hints:
                settings['hints'] = 'on'
            elif nohints:
                settings['hints'] = 'off'

            settings['tournament'] = tournament
            settings['spoilers'] = spoilers

            if not 'allow_quickswap' in settings:
                settings['allow_quickswap'] = allow_quickswap

            if self.preset_data.get('customizer', False):
                endpoint = "/api/customizer"
            elif self.preset_data.get('festive', False):
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
            customizer=1 if self.preset_data.get('customizer', False) else 0
        )
        return seed


class SMPreset(SahasrahBotPresetCore):
    randomizer = 'sm'

    async def generate(self, tournament=True):
        if self.preset_data is None:
            await self.fetch()

        settings = self.preset_data['settings']
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
    randomizer = 'smz3'

    async def generate(self, tournament=True):
        if self.preset_data is None:
            await self.fetch()

        settings = self.preset_data['settings']
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
    randomizer = 'ctjets'

    async def generate(self):
        if self.preset_data is None:
            await self.fetch()

        settings = self.preset_data['settings']
        seed_uri = await ctjets.roll_ctjets(settings, version=self.preset_data.get('version', '3.1.0'))

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
