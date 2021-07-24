import asyncio
import os
import random
import tempfile
import logging

###
# 1) Make a new temp directory
# 2) Set working dir to that temp dir
# 3) Run the command: mono /opt/dash-rando-app/dash-rando-app-v10/DASH_Randomizer.exe -q -v -m "full" -p /home/tprescott/super_metroid.sfc
# 4) Find the first file with a .sfc extension in the directory
# 5) Create a .bps file
# 6) Copy the bps file to /var/www/sgldash/bps/
# 7) Delete the temporary directory created in step 1
# 8) Return with the url for the patch (https://patch.synack.live/?patch=DASH_v10_SF_57677.bps)
###


def roll_smdash():
    return random.randrange(1000000, 9999999)


async def create_smdash(mode="mm"):
    if mode not in ['mm', 'full', 'sgl20', 'vanilla']:
        raise Exception("Specified mode is not valid.  Must be mm, full, sgl20, or vanilla")

    with tempfile.TemporaryDirectory() as tmp:
        wd = os.getcwd()
        os.chdir(tmp)
        try:
            proc = await asyncio.create_subprocess_exec(
                'mono',
                '/opt/dash-rando-app/dash-rando-app-v10/DASH_Randomizer.exe',
                '-q',
                '-v',
                '-m', mode,
                '-p', os.environ.get('SM_ROM'),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)

            _, stderr = await proc.communicate()
            if proc.returncode > 0:
                raise Exception(f'Exception while generating game: {stderr.decode()}')
        finally:
            os.chdir(wd)

        os.chdir(wd)
        logging.info(os.getcwd())

        smdashrom = os.path.join(tmp, [f for f in os.listdir(tmp) if f.endswith(".sfc")][0])
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

        patchname = os.path.splitext(os.path.basename(smdashrom))[0] + ".bps"

        proc = await asyncio.create_subprocess_exec(
            os.path.join(wd, 'utils', 'flips'),
            '--create',
            '--bps-delta',
            os.environ.get('SM_ROM'),
            os.path.join(tmp, smdashromenc),
            os.path.join('/var/www/sgldash/bps', patchname),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        _, stderr = await proc.communicate()
        if proc.returncode > 0:
            raise Exception(f'Exception while while creating patch: {stderr.decode()}')

    return f"https://patch.synack.live/?patch={patchname}"
