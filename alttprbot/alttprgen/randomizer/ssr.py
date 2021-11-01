import os
import random
import re
import string
from datetime import datetime
import tempfile
import asyncio
import logging
from dataclasses import dataclass

from github import Github, InputFileContent


@dataclass
class Seed:
    permalink: str
    file_name: str
    seed: str
    hash: str
    version: str

    spoiler_log_url: str = None


async def generate_seed(permalink, spoiler=False):
    seed_name = "".join(random.choice(string.digits) for _ in range(18))
    file_name = "".join(random.choice(string.digits) for _ in range(18))

    with tempfile.TemporaryDirectory() as tmp:
        proc = await asyncio.create_subprocess_exec(
            'python3',
            '/opt/ssrando/randoscript.py',
            '--dry-run',
            '--noui',
            f'--seed={seed_name}',
            f'--permalink={permalink}',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=tmp
        )

        stdout, stderr = await proc.communicate()
        logging.info(stdout.decode())
        if proc.returncode > 0:
            raise Exception(f'Exception while generating game: {stderr.decode()}')

        try:
            spoiler_log_file_name = os.path.join(tmp, f"SS Random {seed_name} - Spoiler Log.txt")

            with open(spoiler_log_file_name, "r") as spoiler_log_file:
                bare_log = spoiler_log_file.read()
                log = bare_log.split('\n')

                version = log[0]
                permalink = log[1].split(' ')[1]
                hash_re = re.compile('Hash : (.*)')
                rando_hash = hash_re.findall(log[3])[0]
        except FileNotFoundError:
            spoiler_log_file_name = os.path.join(tmp, f"SS Random {seed_name} - Anti Spoiler Log.txt")

            with open(spoiler_log_file_name, "r") as spoiler_log_file:
                bare_log = spoiler_log_file.read()
                log = bare_log.split('\n')

                version = log[0]
                permalink = log[1].split(' ')[1]
                hash_re = re.compile('Hash : (.*)')
                rando_hash = hash_re.findall(log[3])[0]

    if spoiler:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")

        gh = Github(os.environ.get("GITHUB_GIST_TOKEN"))
        gh_auth_user = gh.get_user()
        gist = gh_auth_user.create_gist(
            public=False,
            files={f"spoiler_log_{timestamp}.txt": InputFileContent(bare_log)},
            description="Skyward Sword Randomizer Spoiler Log"
        )
        spoiler_log_url = gist.html_url

        return Seed(
            permalink=permalink,
            file_name=file_name,
            seed=seed_name,
            hash=rando_hash,
            spoiler_log_url=spoiler_log_url,
            version=version
        )

    else:
        return Seed(
            permalink=permalink,
            file_name=file_name,
            seed=seed_name,
            hash=rando_hash,
            version=version
        )
