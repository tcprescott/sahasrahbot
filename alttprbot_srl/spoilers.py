import asyncio
from alttprbot.database import spoiler_races
import math
import ircmessage


async def send_spoiler_log(srl_id, client, target):
    race = await spoiler_races.get_spoiler_race_by_id(srl_id)
    if race:
        await client.message(target, 'Sending spoiler log...')
        await client.message(target, '---------------')
        await client.message(target, f"This race\'s spoiler log: {race['spoiler_url']}")
        await client.message(target, '---------------')
        await client.message(target, 'GLHF! :mudora:')
        await countdown_timer(
            ircbot=client,
            duration_in_seconds=race['studytime'],
            srl_channel=target,
            beginmessage=True,
        )
        await spoiler_races.start_spoiler_race(srl_id)


async def countdown_timer(ircbot, duration_in_seconds, srl_channel, beginmessage=False):
    loop = asyncio.get_running_loop()

    reminders = [1800, 1500, 1200, 900, 600, 300,
                 120, 60, 30, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    start_time = loop.time()
    end_time = loop.time() + duration_in_seconds
    while True:
        # print(datetime.datetime.now())
        timeleft = math.ceil(start_time - loop.time() + duration_in_seconds)
        # print(timeleft)
        if timeleft in reminders:
            minutes = math.floor(timeleft/60)
            seconds = math.ceil(timeleft % 60)
            if minutes == 0 and seconds > 10:
                msg = f'{seconds} second(s) remain!'
            elif minutes == 0 and seconds <= 10:
                msg = ircmessage.style(
                    f"{seconds} second(s) remain!", fg='green', bold=True)
            else:
                msg = f'{minutes} minute(s), {seconds} seconds remain!'
            await ircbot.message(srl_channel, msg)
            reminders.remove(timeleft)
        if loop.time() >= end_time:
            if beginmessage:
                await ircbot.message(srl_channel, ircmessage.style('Log study has finished.  Begin racing!', fg='red', bold=True))
            break
        await asyncio.sleep(.5)
