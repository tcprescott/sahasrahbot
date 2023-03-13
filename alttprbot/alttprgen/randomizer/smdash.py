import asyncio
import os
import random
import tempfile
import logging
import shortuuid

###
# 1) Make a new temp directory
# 2) Set working dir to that temp dir
# 3) Run the command: node /opt/dash-rando-app/dash.cli.js -r /home/tprescott/super_metroid.sfc -p "full"
# 4) Find the first file with a .sfc extension in the directory
# 5) Create a .bps file
# 6) Copy the bps file to /var/www/sgldash/bps/
# 7) Delete the temporary directory created in step 1
# 8) Return with the url for the patch (https://patch.synack.live/?patch=DASH_v11_SF_057677.bps)
###

###
# https://dashrando.github.io/app/dash.cli.js
###


def roll_smdash():
    return random.randrange(1000000, 9999999)


async def create_smdash(mode="mm", encrypt=False):
    if mode not in ['mm', 'full', 'recall_mm', 'recall_full', 'std_mm', 'std_full']:
        raise Exception("Specified mode is not valid.  Modes: mm, full, recall_mm, recall_full, std_mm, std_full")

    with tempfile.TemporaryDirectory() as tmp:
        current_working_directory = os.getcwd()
        os.chdir(tmp)
        try:
            proc = await asyncio.create_subprocess_exec(
                '/usr/bin/node',
                os.path.join(current_working_directory, 'utils', 'dash.cli.js'),
                '-r', os.environ.get('SM_ROM'),
                '-p', mode,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)

            _, stderr = await proc.communicate()
            if proc.returncode > 0:
                raise Exception(f'Exception while generating game: {stderr.decode()}')
        finally:
            os.chdir(current_working_directory)

        os.chdir(current_working_directory)
        logging.info(os.getcwd())

        smdashrom = os.path.join(tmp, [f for f in os.listdir(tmp) if f.endswith(".sfc")][0])

        ## note to those who are reading this: this encryption process is not publically available.
        if encrypt:
            smdashromenc = os.path.splitext(os.path.basename(smdashrom))[0] + "_encrypted.sfc"

            proc = await asyncio.create_subprocess_exec(
                'dotnet',
                '/opt/randocrypt/RandoCryptCli.dll',
                smdashrom,
                os.path.join(tmp, smdashromenc),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)

            _, stderr = await proc.communicate()
            if proc.returncode > 0:
                raise Exception(f'Exception while securing game: {stderr.decode()}')

        random_id = shortuuid.ShortUUID().random(length=12)
        patchname = f"DASH_{mode.upper()}_{random_id}.bps"

        proc = await asyncio.create_subprocess_exec(
            os.path.join(current_working_directory, 'utils', 'flips'),
            '--create',
            '--bps-delta',
            os.environ.get('SM_ROM'),
            os.path.join(tmp, smdashromenc if encrypt else smdashrom),
            os.path.join('/var/www/sgldash/bps', patchname),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        _, stderr = await proc.communicate()
        if proc.returncode > 0:
            raise Exception(f'Exception while while creating patch: {stderr.decode()}')

    return f"https://patch.synack.live/?patch={patchname}"
