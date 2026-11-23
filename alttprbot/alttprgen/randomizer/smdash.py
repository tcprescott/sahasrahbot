import ssl
import aiohttp


async def create_smdash(mode="classic_mm", spoiler=False):
    """
    Generates a DASH Super Metroid Randomizer seed and returns the URL to download it.
    """
    async with aiohttp.ClientSession() as session:
        route = f'https://www.dashrando.net/generate/{mode}?race=1'
        if spoiler:
            route += '&spoiler=1'
        async with session.get(route, ssl=ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2),
                               allow_redirects=False) as resp:
            msg = await resp.text()
            if resp.status == 307:
                return msg
            else:
                raise Exception(f"Could not generate smdash seed: {msg}")

async def get_smdash_presets():
    """
    Returns the available DASH presets as a list of strings.
    """
    try:
        async with aiohttp.ClientSession() as session:
            route = f'https://www.dashrando.net/api/presets'
            async with session.get(route, ssl=ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2),
                                allow_redirects=False) as resp:
                obj = await resp.json()
                presets = []
                for p in obj['data']:
                    presets.append(p['tags'][0])
                return presets
    except:
        return ['classic', 'recall', '2017_mm', 'chozo_bozo', 'sgl23', 'surprise_surprise']