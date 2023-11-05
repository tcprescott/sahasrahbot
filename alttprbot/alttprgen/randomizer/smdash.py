import aiohttp


async def create_smdash(mode="classic_mm"):
    presets = ['sgl23', 'recall_mm', 'recall_full', 'classic_mm', 'classic_full']
    if mode not in presets:
        raise Exception("Specified preset is not valid.  Presets: " + ", ".join(presets))

    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://www.dashrando.net/generate/{mode}', allow_redirects=False) as resp:
            msg = await resp.text()
            if resp.status == 307:
                return msg
            else:
                raise Exception(f"Could not generate smdash patch.\n\n{msg}")
