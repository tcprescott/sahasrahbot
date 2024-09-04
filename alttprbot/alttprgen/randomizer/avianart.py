import asyncio
import aiohttp

class AVIANART():
    def __init__(self, preset=None, race=True):
        self.preset = preset
        self.race = race
        self.status = None
        self.hash_id = None
        self.result = None

    async def generate_game(self):
        payload = [{"args":{"race": self.race}}]
        async with aiohttp.ClientSession() as session:
            async with session.post(f'https://avianart.games/api.php?action=generate&preset={self.preset}', json=payload) as resp:
                result = await resp.json()

            hash_id = result['response']['hash']

            # check until we get an error or it is finished generating
            attempts = 0
            while result['response'].get('status', 'finished') == 'generating' and attempts < 24:
                await asyncio.sleep(5)
                attempts += 1
                async with session.get(f'https://avianart.games/api.php?action=permlink&hash={hash_id}') as resp:
                    result = await resp.json()

                self.status = result['response'].get('status', 'finished')

                if self.status == 'finished':
                    self.hash_id = hash_id
                    self.result = result
                    return hash_id
                
                if self.status == 'failure':
                    raise Exception("Failed to generate game: " + result['response'].get('message'))

    @classmethod
    async def create(
            cls,
            preset,
            race=True,
    ):
        seed = cls(preset=preset, race=race)
        await seed.generate_game()
        return seed

    @property
    def url(self):
        if self.status != 'finished':
            return None
        return f"https://avianart.games/perm/{self.hash_id}"

    # Pull the code from the spoiler file, and translate it to what SahasrahBot expects
    @property
    def code(self):
        file_select_code: str = self.result['response']['spoiler']['meta']['hash']
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
        return self.result['response']['spoiler']['meta']['version']

    @property
    def avianart(self):
        return True
