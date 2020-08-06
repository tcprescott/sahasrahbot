import datetime

import aiohttp.client_exceptions
import discord

from alttprbot.database import config
from alttprbot.util import http, srl
from alttprbot_discord.bot import discordbot
from config import Config as c


async def check_race(srl_id):
    race = await srl.get_race(srl_id)

    # only report on alttphacks races for now, make this configurable in the future
    if not race['game']['abbrev'] == 'alttphacks':
        return

    configguilds = await config.get_all_parameters_by_name('AltHunterReportingChannel')
    for entrant in race['entrants']:
        try:
            pastraces = await srl.get_pastraces(game=race['game']['abbrev'], player=entrant, pagesize=0)
        except aiohttp.client_exceptions.ClientResponseError:
            print(f'could not get history of {entrant}, skipping...')
            continue
        if pastraces['count'] == 0:
            print(f'{entrant} is new')
            pastraces_all = await srl.get_pastraces(game=None, player=entrant, pagesize=0)
            if pastraces_all['count'] > 50:
                continue
            twitch_nick = race['entrants'][entrant]['twitch']
            if twitch_nick == '':
                twitch_info = None
            else:
                try:
                    twitch_info = await get_twitch_user(twitch_nick)
                except aiohttp.client_exceptions.ClientResponseError:
                    print(f'could not find twitch info for {entrant}')
                    twitch_info = None

            embed = discord.Embed(
                title="New Racer Detected!",
                description=f"A new racer named [{entrant}](http://www.speedrunslive.com/profiles/#!/{entrant}/1) began racing in [#srl-{race['id']}](http://www.speedrunslive.com/race/?id={race['id']})",
                color=discord.Colour.red(),
                timestamp=datetime.datetime.now()
            )

            if twitch_info is not None:
                created_at = datetime.datetime.strptime(
                    twitch_info['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
                embed.add_field(
                    name='Twitch Nickname',
                    value=f"[{twitch_nick}](https://twitch.tv/{twitch_nick})",
                    inline=False
                )
                embed.add_field(
                    name='Account Created Date',
                    value=f"{created_at}",
                    inline=False
                )
                embed.set_thumbnail(url=twitch_info['logo'])

            if pastraces_all['count'] > 0:
                embed.add_field(
                    name=f"Total SRL Races (outside of {race['game']['abbrev']})",
                    value=pastraces_all['count'],
                    inline=False
                )

            for configguild in configguilds:
                channel = discordbot.get_channel(int(configguild['value']))

                await channel.send(embed=embed)


async def get_twitch_user(twitch_user_id):
    headers = {
        'Accept': 'application/vnd.twitchtv.v5+json',
        'Client-ID': c.SB_TWITCH_CLIENT_ID
    }
    params = {
        'login': twitch_user_id
    }
    result = await http.request_generic('https://api.twitch.tv/kraken/users', returntype='json', reqparams=params, header=headers)
    return result['users'][0]


# move this elsewhere
# def humanize_date_difference(now, otherdate=None, offset=None):
#     if otherdate:
#         dt = otherdate - now
#         offset = dt.seconds + (dt.days * 60*60*24)
#     if offset:
#         delta_s = offset % 60
#         offset /= 60
#         delta_m = offset % 60
#         offset /= 60
#         delta_h = offset % 24
#         offset /= 24
#         delta_d = offset
#     else:
#         raise ValueError("Must supply otherdate or offset (from now)")

#     if delta_d > 1:
#         if delta_d > 6:
#             date = now + datetime.timedelta(days=-delta_d, hours=-delta_h, minutes=-delta_m)
#             return date.strftime('%A, %Y %B %m, %H:%I')
#         else:
#             wday = now + datetime.timedelta(days=-delta_d)
#             return wday.strftime('%A')
#     if delta_d == 1:
#         return "Yesterday"
#     if delta_h > 0:
#         return "%dh%dm ago" % (delta_h, delta_m)
#     if delta_m > 0:
#         return "%dm%ds ago" % (delta_m, delta_s)
#     else:
#         return "%ds ago" % delta_s
