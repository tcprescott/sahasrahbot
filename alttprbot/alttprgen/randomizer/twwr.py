import asyncio
import logging
import os
import random
import string
import tempfile
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime

import shortuuid
from github import Github, InputFileContent

STANDARD_PERMALINKS = OrderedDict([
    ("s4", "MS45LjAAQQAFCyIAD3DAAgAAAAAAAQAA"),
    ("beginner", "MS45LjAAQQAFAwIADzDAAYAcQIFBATAA"),
    ("co-op", "MS45LjAAQQAVCyYAD3DABAAAAAAAAAAA"),
    ("allsanity", "MS45LjAAQQD//3+CD3BABQAAAAAAAAAA"),
    ("s3", "MS45LjAAQQAXAwQATjDAAwgAAAAAAQAA"),
])
STANDARD_DEFAULT = ["s4"]

SPOILER_LOG_PERMALINKS = OrderedDict([
    ("preset-a", "MS45LjAAQQA3AyYCD1DAAgAAAAAAAAAA"),
    ("preset-b", "MS45LjAAQQAXYyaCD1DAAgAAAAAAAAAA"),
    ("preset-c", "MS45LjAAQQAXAyYCD5DAAgAAAAAAAAAA"),
    ("preset-d", "MS45LjAAQQAXByYCD1DAAgAAAAAAAAAA"),
    ("preset-e", "MS45LjAAQQAXA2YCD1DAAwAAAAAAAAAA"),
    ("preset-f", "MS45LjAAQQAfCyYCD1DAAgAAAAAAAAAA"),
    ("s1", "MS45LjAAQQAXAwYCDxDAAgAAAAAAAQAA"),
    ("allsanity", "MS45LjAAQQD//3+CD1BABQAAAAAAAAAA"),
])

SETTINGS_DESCRIPTIONS = OrderedDict([
    ("preset-a", "Long Sidequests"),
    ("preset-b", "Triforce Charts, Big Octos and Gunboats"),
    ("preset-c", "Swordless"),
    ("preset-d", "Lookout Platforms and Rafts"),
    ("preset-e", "4 Dungeon Race Mode, Key-Lunacy"),
    ("preset-f", "Combat Secret Caves, Submarines"),
])

SPOILER_LOG_DEFAULT = ["preset-a", "preset-b", "preset-c", "preset-d", "preset-e", "preset-f"]
DEFAULT_PLANNING_TIME = 60
MINIMUM_PLANNING_TIME = 20

BANNABLE_PRESETS = SPOILER_LOG_DEFAULT


@dataclass
class Seed:
    permalink: str
    file_name: str
    seed: str

    spoiler_log_url: str = None


async def generate_seed(permalink, generate_spoiler_log=False):
    random_suffix = shortuuid.ShortUUID().random(length=10)
    seed_name = f"{random_suffix}"
    file_name = "".join(random.choice(string.digits) for _ in range(6))

    with tempfile.TemporaryDirectory() as tmp:
        proc = await asyncio.create_subprocess_exec(
            'python3',
            '/opt/wwrando/wwrando.py',
            f'-seed={seed_name}',
            f'-permalink={permalink}',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=dict(os.environ, QT_QPA_PLATFORM='offscreen'),
            cwd=tmp
        )

        stdout, stderr = await proc.communicate()
        logging.info(stdout.decode())
        if proc.returncode > 0:
            raise Exception(f'Exception while generating game: {stderr.decode()}')

        permalink_file_name = os.path.join(tmp, f"permalink_{seed_name}.txt")
        with open(permalink_file_name, "r") as permalink_file:
            permalink = permalink_file.read()

        seed_hash_file_name = os.path.join(tmp, f"seed_hash_{seed_name}.txt")
        with open(seed_hash_file_name, "r") as seed_hash_file:
            seed_hash = seed_hash_file.read()

        if generate_spoiler_log:
            spoiler_log_file_name = os.path.join(tmp, f"spoiler_log_{seed_name}.txt")
            with open(spoiler_log_file_name, "r") as spoiler_log_file:
                spoiler_log = spoiler_log_file.read()

            timestamp = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
            gh = Github(os.environ.get("GITHUB_GIST_TOKEN"))
            gh_auth_user = gh.get_user()
            gist = gh_auth_user.create_gist(
                public=False,
                files={f"spoiler_log_{timestamp}.txt": InputFileContent(spoiler_log)},
                description="The Wind Waker Randomizer Spoiler Log"
            )
            spoiler_log_url = gist.html_url
        else:
            spoiler_log_url = None

    return Seed(
        permalink=permalink,
        file_name=file_name,
        seed=seed_name,
        spoiler_log_url=spoiler_log_url,
    )
