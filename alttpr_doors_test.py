from dotenv import load_dotenv  # nopep8

load_dotenv()  # nopep8

import asyncio
import json

from alttprbot.alttprgen.randomizer.alttprdoor import AlttprDoor


async def main():
    with open("/home/tprescott/git/sahasrahbot/test_input/doorstest.json") as json_file:
        settings = json.load(json_file)

    seed = await AlttprDoor.create(settings=settings, spoilers=True)
    print(seed.spoiler_url)
    print(seed.url)
    print(seed.code)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
