import aiohttp


async def create_smdash(mode="classic_mm"):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://www.dashrando.net/generate/{mode}', allow_redirects=False) as resp:
            msg = await resp.text()
            if resp.status == 307:
                return msg
            else:
                raise Exception(f"Could not generate smdash seed: {msg}")
