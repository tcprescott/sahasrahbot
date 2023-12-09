import asyncio
import gzip
import json
import logging
import os
import random
import re
import string
import tempfile
import sys

import aioboto3
import aiofiles
from tenacity import RetryError, AsyncRetrying, stop_after_attempt, retry_if_exception_type

import config


class AlttprDoor():
    def __init__(self, settings=None, spoilers=True):
        self.settings = settings
        self.spoilers = spoilers

    async def generate_game(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_file_path = os.path.join(tmp, "settings.json")
            self.hash = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

            self.settings['outputpath'] = tmp
            self.settings['outputname'] = self.hash
            self.settings['create_rom'] = True
            self.settings['create_spoiler'] = True
            self.settings['calc_playthrough'] = False
            self.settings['rom'] = config.ALTTP_ROM
            self.settings['enemizercli'] = os.path.join(
                "utils",
                "enemizer",
                'os.10.12-x64' if sys.platform == 'darwin' else 'ubuntu.16.04-x64',
                'EnemizerCLI.Core'
            )

            # set some defaults we do NOT want to change ever
            self.settings['count'] = 1
            self.settings['multi'] = 1
            self.settings['names'] = ""
            self.settings['race'] = not self.spoilers

            with open(settings_file_path, "w") as f:
                json.dump(self.settings, f)

            attempts = 0
            try:
                async for attempt in AsyncRetrying(stop=stop_after_attempt(10),
                                                   retry=retry_if_exception_type(Exception)):
                    with attempt:
                        attempts += 1
                        proc = await asyncio.create_subprocess_exec(
                            'python3',
                            'DungeonRandomizer.py',
                            '--settingsfile', settings_file_path,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                            cwd="utils/ALttPDoorRandomizer")

                        stdout, stderr = await proc.communicate()
                        logging.info(stdout.decode())
                        if proc.returncode > 0:
                            raise Exception(f'Exception while generating game: {stderr.decode()}')

            except RetryError as e:
                raise e.last_attempt._exception from e

            self.attempts = attempts

            self.patch_name = "DR_" + self.settings['outputname'] + ".bps"
            self.rom_name = "DR_" + self.settings['outputname'] + ".sfc"
            self.spoiler_name = "DR_" + self.settings['outputname'] + "_Spoiler.txt"

            rom_path = os.path.join(tmp, self.rom_name)
            patch_path = os.path.join(tmp, self.patch_name)
            spoiler_path = os.path.join(tmp, self.spoiler_name)

            proc = await asyncio.create_subprocess_exec(
                os.path.join('utils', 'macos' if sys.platform == 'darwin' else 'linux', 'flips'),
                '--create',
                '--bps-delta',
                config.ALTTP_ROM,
                rom_path,
                patch_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)

            stdout, stderr = await proc.communicate()
            logging.info(stdout.decode())
            if proc.returncode > 0:
                raise Exception(f'Exception while while creating patch: {stderr.decode()}')

            async with aiofiles.open(patch_path, "rb") as f:
                patchfile = await f.read()

            session = aioboto3.Session()
            async with session.client('s3') as s3:
                await s3.put_object(
                    Bucket=config.SAHASRAHBOT_BUCKET,
                    Key=f"patch/{self.patch_name}",
                    Body=patchfile,
                    ACL='public-read'
                )

            async with aiofiles.open(spoiler_path, "rb") as f:
                self.spoilerfile = await f.read()

            async with session.client('s3') as s3:
                await s3.put_object(
                    Bucket=config.SAHASRAHBOT_BUCKET,
                    Key=f"spoiler/{self.spoiler_name}",
                    Body=gzip.compress(self.spoilerfile),
                    ACL='public-read' if self.spoilers else 'private',
                    ContentEncoding='gzip',
                    ContentDisposition='attachment'
                )

    @classmethod
    async def create(
            cls,
            settings,
            spoilers=True
    ):
        seed = cls(settings=settings, spoilers=spoilers)
        await seed.generate_game()
        return seed

    @property
    def url(self):
        return f"https://alttprpatch.synack.live/patcher.html?patch={self.patch_url}"

    @property
    def spoiler_url(self):
        return f"https://{config.SAHASRAHBOT_BUCKET}.s3.amazonaws.com/spoiler/{self.spoiler_name}"

    @property
    def patch_url(self):
        return f"https://{config.SAHASRAHBOT_BUCKET}.s3.amazonaws.com/patch/{self.patch_name}"

    # Pull the code from the spoiler file, and translate it to what SahasrahBot expects
    @property
    def code(self):
        file_select_code = re.search("Hash:*\s(.*,.*,.*,.*,.*)", self.spoilerfile.decode()).groups()[0]
        code = list(file_select_code.split(', '))
        code_map = {
            'Bomb': 'Bombs',
            'Powder': 'Magic Powder',
            'Rod': 'Ice Rod',
            'Ocarina': 'Flute',
            'Bug Net': 'Bugnet',
            'Bottle': 'Empty Bottle',
            'Potion': 'Green Potion',
            'Cane': 'Somaria',
            'Pearl': 'Moon Pearl',
            'Key': 'Big Key'
        }
        p = list(map(lambda x: code_map.get(x, x), code))
        return [p[0], p[1], p[2], p[3], p[4]]

    @property
    def version(self):
        return \
        re.search("ALttP Dungeon Randomizer Version (.*)  -  Seed: ([0-9]*)", self.spoilerfile.decode()).groups()[0]

    @property
    def doors(self):
        return True
