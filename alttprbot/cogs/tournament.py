import re
import asyncio
import datetime

import discord
import gspread_asyncio
import gspread.exceptions
from discord.ext import commands
from oauth2client.service_account import ServiceAccountCredentials

from config import Config as c

from ..database import srlnick
from ..util import http, embed_formatter, checks
from ..alttprgen.preset import get_preset
import pyz3r

# this module was only intended for the Main Tournament 2019
# we will probably expand this later to support other tournaments in the future

class Tournament(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        if ctx.guild.id in c.TournamentServers:
            return True
        else:
            return False

    @commands.command()
    @checks.has_any_channel('testing','console')
    @commands.has_any_role('Admins','Mods')
    async def loadnicks(self, ctx):
        await loadnicks(ctx)

    @commands.command()
    @checks.has_any_channel('testing','console')
    @commands.has_any_role('Admins','Mods')
    async def startqual(self, ctx, raceid, num: int):
        race = await get_race(raceid)
        if race == {}:
            raise Exception('That race does not exist.')

        await loadnicks(ctx)
        await ctx.send('Loaded SRL nicks from gsheet.')

        await send_irc_message(raceid,'NOTICE: The seed for this race will be distributed in 60 seconds.  Please .join if you intend to race.  If you have not joined, you will not receive the seed.')
        await ctx.send('Sent .join warning in SRL.')
        if not c.DEBUG: await asyncio.sleep(60)
        await send_irc_message(raceid,'The seed is being generated and distributed.  Please standby.')
        await ctx.send('Starting seed generation.')

        seed, preset_dict = await get_preset('open', hints=False, spoilers_ongen=False)
        if not seed:
            raise Exception('Could not generate game.')
        embed = await embed_formatter.seed_embed(
            seed,
            name=f"Tournament Qualifier #{num}",
            notes='Below is the permalink for this qualifier\'s race.  Please load the rom and ready up as soon as possible.\n\nRemember, Please do not talk in the qualifier race channels except for the necessary race commands.\nAnything that is a spoiler will result in a forfeit and possible removal from the tournament.\nWhat constitutes a spoiler is at the discretion of the tournament admins.\n',
            emojis=self.bot.emojis)
        await ctx.send(embed=embed)
        
        await self.send_qualifier_dms(ctx, embed=embed, race=race, url=seed.url, code='/'.join(await seed.code()))
        await send_irc_message(raceid,'The seed has been distributed.  Please contact a tournament administrator if you did not receive the seed in Discord.')
        await gsheet_qualifier(race, num)
        await ctx.send(build_multistream_links(race))

    @commands.command()
    @checks.has_any_channel('testing','console')
    @commands.has_any_role('Admins','Mods')
    async def resendqual(self, ctx, raceid, num, hash):
        race = await get_race(raceid)
        if race == {}:
            raise Exception('That race does not exist.')

        await loadnicks(ctx)
        await ctx.send('Loaded SRL nicks from gsheet.')

        seed = await pyz3r.alttpr(
            hash=hash
        )
        if not seed:
            raise Exception('Could not retrieve game.')
        embed = await embed_formatter.seed_embed(
            seed,
            name=f"Tournament Qualifier #{num}",
            notes='Below is the permalink for this qualifier\'s race.  Please load the rom and ready up as soon as possible.\n\nRemember, Please do not talk in the qualifier race channels except for the necessary race commands.\nAnything that is a spoiler will result in a forfeit and possible removal from the tournament.\nWhat constitutes a spoiler is at the discretion of the tournament admins.\n',
            emojis=self.bot.emojis)
        await ctx.send(embed=embed)

        await self.send_qualifier_dms(ctx, embed=embed, race=race, url=seed.url, code='/'.join(await seed.code()))
        await gsheet_qualifier(race, num)
        await ctx.send(build_multistream_links(race))

    @commands.command()
    @checks.has_any_channel('testing','console')
    @commands.has_any_role('Admins','Mods')
    async def qualmulti(self, ctx, raceid):
        race = await get_race(raceid)
        if race == {}:
            raise Exception('That race does not exist.')
        await ctx.send(build_multistream_links(race))

    @commands.command()
    @checks.has_any_channel('testing','console')
    @commands.has_any_role('Admins','Mods')
    async def checkreg(self, ctx, raceid):
        race = await get_race(raceid)
        if race == {}:
            raise Exception('That race does not exist.')
        await loadnicks(ctx)
        await self.send_qualifier_dms(ctx, embed=None, race=race, checkonly=True)

    @commands.command()
    @commands.is_owner()
    async def sendirc(self, ctx, channel, message):
        await send_irc_message(channel, message)

    async def send_qualifier_dms(self, ctx, embed, race, checkonly=False, url=None, code=None):
        bad_nicks = []
        unable_to_dm = []

        for entrant in race['entrants']:
            if entrant == 'JOPEBUSTER':
                continue
            discord_users = await srlnick.get_discord_id(entrant)
            if discord_users is False:
                bad_nicks.append(entrant)
            else:
                for discord_user in discord_users:
                    user = self.bot.get_user(discord_user['discord_user_id'])
                    if user is not None:
                        try:
                            if not checkonly: await user.send(embed=embed)
                        except:
                            unable_to_dm.append(entrant)
                    else:
                        unable_to_dm.append(entrant)

        if len(bad_nicks) > 0:
            await ctx.send("We do not have a Discord name for these joined players in #srl-{id}\n```{nicks}```".format(
                id=race['id'],
                nicks='\n'.join(bad_nicks),
            ))
        if len(unable_to_dm) > 0:
            await ctx.send("Bot was unable to DM the following players in #srl-{id}\n```{dms}```".format(
                id=race['id'],
                dms='\n'.join(unable_to_dm),
            ))
        if len(unable_to_dm) == 0 and len(bad_nicks) == 0 and checkonly:
            await ctx.send(f"All users joined to the race in #srl-{race['id']} are able to be resolved.")
        if (len(unable_to_dm) > 0 or len(bad_nicks) > 0) and not checkonly:
            await ctx.send(f"Please send this to those who did not receive the DMs.\n```Below is the permalink for this qualifier\'s race.  Please load the rom and ready up as soon as possible.\n\nRemember, Please do not talk in the qualifier race channels except for the necessary race commands.\nAnything that is a spoiler will result in a forfeit and possible removal from the tournament.\nWhat constitutes a spoiler is at the discretion of the tournament admins.\n\n{url}\n{code}```")

async def loadnicks(ctx):
    agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
    agc = await agcm.authorize()
    wb = await agc.open_by_key(c.TournamentQualifierSheet)
    wks = await wb.get_worksheet(0)

    bad_discord_names=[]

    converter = commands.MemberConverter()
    for row in await wks.get_all_records():
        try:
            member = await converter.convert(ctx, row['Discord Name'])
            await srlnick.insert_srl_nick(member.id, row['SRL Name'])
        except discord.ext.commands.errors.BadArgument:
            bad_discord_names.append(row['Discord Name'])

    if len(bad_discord_names) > 0:
        await ctx.send("Bad discord names.  These names were not processed.\n\n`{names}`".format(
            names='\n'.join(bad_discord_names)
        ))

def build_multistream_links(race):
    twitchnames = []
    for entrant in race['entrants']:
        twitch = race['entrants'][entrant]['twitch']
        if not twitch=="":
            twitchnames.append(twitch)
        
    chunks = [twitchnames[i * 4:(i + 1) * 4] for i in range((len(twitchnames) + 4 - 1) // 4 )]
    multi = "Multistream links:\n\n"
    for chunk in chunks:
        multi += '<https://multistre.am/{streams}/layout12/>\n'.format(
            streams='/'.join(chunk)
        )
    return multi

async def gsheet_qualifier(race, num):
    agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
    agc = await agcm.authorize()
    wb = await agc.open_by_key(c.TournamentQualifierSheet)

    try:
        wks = await wb.worksheet(f'Qualifier #{num} - {datetime.datetime.now().date()}')
        await wks.clear()
    except gspread.exceptions.WorksheetNotFound:
        wks = await wb.add_worksheet(title=f'Qualifier #{num} - {datetime.datetime.now().date()}', rows=50, cols=10)

    await wks.append_row(['Nickname','Twitch Stream','Finish Time'])

    for entrant in race['entrants']:
        if entrant=="JOPEBUSTER":
            continue
        twitch = race['entrants'][entrant]['twitch']
        await wks.append_row([entrant,twitch])

async def get_race(raceid):
    if raceid == "test":
        return {
                "id": "test",
                "game": {
                    "id": 3977,
                    "name": "The Legend of Zelda: A Link to the Past Hacks",
                    "abbrev": "alttphacks",
                    "popularity": 122.000000,
                    "popularityrank": 8
                },
                "goal": "test goal",
                "time": 0,
                "state": 1,
                "statetext": "Entry Open",
                "filename": "",
                "numentrants": 2,
                "entrants": {
                    "synack": {
                        "displayname": "synack",
                        "place": 9994,
                        "time": -3,
                        "message": "",
                        "statetext": "Entered",
                        "twitch": "The_Synack",
                        "trueskill": "963"
                    },
                    "synack2": {
                        "displayname": "synack2",
                        "place": 9994,
                        "time": -3,
                        "message": "",
                        "statetext": "Entered",
                        "twitch": "SynackTheSecond",
                        "trueskill": "705"
                    },
                    "unknownplayer": {
                        "displayname": "unknownplayer",
                        "place": 9994,
                        "time": -3,
                        "message": "",
                        "statetext": "Entered",
                        "twitch": "abc123",
                        "trueskill": "0"
                    },
                    "unknownplayer1": {
                        "displayname": "unknownplayer",
                        "place": 9994,
                        "time": -3,
                        "message": "",
                        "statetext": "Entered",
                        "twitch": "sfs",
                        "trueskill": "0"
                    },
                    "unknownplayer2": {
                        "displayname": "unknownplayer",
                        "place": 9994,
                        "time": -3,
                        "message": "",
                        "statetext": "Entered",
                        "twitch": "bbbdf",
                        "trueskill": "0"
                    },
                    "unknownplayer3": {
                        "displayname": "unknownplayer",
                        "place": 9994,
                        "time": -3,
                        "message": "",
                        "statetext": "Entered",
                        "twitch": "ghjjgh",
                        "trueskill": "0"
                    },
                    "unknownplayer4": {
                        "displayname": "unknownplayer",
                        "place": 9994,
                        "time": -3,
                        "message": "",
                        "statetext": "Entered",
                        "twitch": "ilkhjghj",
                        "trueskill": "0"
                    },
                    "JOPEBUSTER": {
                        "displayname": "JOPEBUSTER",
                        "place": 9994,
                        "time": -3,
                        "message": "",
                        "statetext": "Entered",
                        "twitch": "",
                        "trueskill": "0"
                    }
                }
            }
    elif raceid == 'rip':
        return {}
    else:
        return await http.request_generic(f'http://api.speedrunslive.com/races/{raceid}', returntype='json')

async def send_irc_message(raceid, message):
    if c.DEBUG: return
    data = {
        'auth': c.InternalApiToken,
        'channel': f'#srl-{raceid}',
        'message': message
    }
    await http.request_json_post('http://localhost:5000/api/message', data=data, auth=None, returntype='text')

# def srl_race_id(channel):
#     if re.search('^#srl-[a-z0-9]{5}$', channel):
#         return channel.partition('-')[-1]

def get_creds():
   return ServiceAccountCredentials.from_json_keyfile_dict(c.gsheet_api_oauth,
      ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive',
      'https://www.googleapis.com/auth/spreadsheets'])

def setup(bot):
    bot.add_cog(Tournament(bot))
