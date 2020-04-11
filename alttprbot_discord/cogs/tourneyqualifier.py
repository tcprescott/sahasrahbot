import asyncio
import datetime
import json

import aiofiles
import discord
import gspread.exceptions
import gspread_asyncio
from discord.ext import commands
from oauth2client.service_account import ServiceAccountCredentials
from pytz import timezone

from alttprbot.alttprgen.preset import get_preset
from alttprbot.database import srlnick
from alttprbot.exceptions import SahasrahBotException
from alttprbot.util import http
from alttprbot_srl.bot import srlbot
from config import Config as c

from ..util import checks
from ..util.alttpr_discord import alttpr

# this module was only intended for the Main Tournament 2019
# we will probably expand this later to support other tournaments in the future


class TournamentQualifier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        if ctx.guild is None:
            return False
        if ctx.guild.id in c.TournamentServers:
            return True
        else:
            return False

    @commands.command()
    @checks.has_any_channel('testing', 'console', 'qual-bot')
    @commands.has_any_role('Admins', 'Mods')
    async def loadnicks(self, ctx):
        await loadnicks(ctx)

    @commands.command()
    @checks.has_any_channel('testing', 'console', 'qual-bot')
    @commands.has_any_role('Admins', 'Mods')
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.channel)
    async def startqual(self, ctx, raceid):
        await self.run_qual(ctx, raceid, hashid=None)

    @commands.command()
    @checks.has_any_channel('testing', 'console', 'qual-bot')
    @commands.has_any_role('Admins', 'Mods')
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.channel)
    async def resendqual(self, ctx, raceid, hashid):
        await self.run_qual(ctx, raceid, hashid=hashid)

    @commands.command()
    @checks.has_any_channel('testing', 'console', 'qual-bot')
    @commands.has_any_role('Admins', 'Mods')
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.channel)
    async def finishqual(self, ctx, raceid):
        await self.finish_qual(ctx, raceid)

    @commands.command()
    @checks.has_any_channel('testing', 'console', 'qual-bot')
    @commands.has_any_role('Admins', 'Mods')
    async def qualmulti(self, ctx, raceid):
        race = await get_race(raceid)
        if race == {}:
            raise SahasrahBotException('That race does not exist.')
        for multi in build_multistream_links(race):
            await ctx.send(multi)

    @commands.command()
    @checks.has_any_channel('testing', 'console', 'qual-bot')
    @commands.has_any_role('Admins', 'Mods')
    async def checkreg(self, ctx, raceid):
        race = await get_race(raceid)
        if race == {}:
            raise SahasrahBotException('That race does not exist.')
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
                            if not checkonly and not c.DEBUG:
                                await user.send(embed=embed)
                        except discord.HTTPException:
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

    async def run_qual(self, ctx, raceid, hashid):
        date = datetime.datetime.now(timezone('US/Pacific')).date()
        race2 = await get_race(raceid)
        if race2 == {}:
            raise SahasrahBotException('That race does not exist.')
        if not race2['game']['abbrev'] == 'alttphacks':
            raise SahasrahBotException('That is not an alttphacks game.')
        if not race2['state'] == 1:
            raise SahasrahBotException('The race is not open for entry.')

        await loadnicks(ctx)
        await ctx.send('Loaded SRL nicks from gsheet.')

        await send_irc_message(raceid, 'NOTICE: The seed for this race will be distributed in 60 seconds.  Please .join if you intend to race.  If you have not joined, you will not receive the seed.')
        await ctx.send('Sent .join warning in SRL.')
        if not c.DEBUG:
            await asyncio.sleep(60)
        race = await get_race(raceid)
        await send_irc_message(raceid, 'The seed is being generated and distributed.  Please standby.')
        await ctx.send('Starting seed generation.')

        if hashid is None:
            seed = await get_preset('open', hints=False, spoilers="off")
            if not seed:
                raise SahasrahBotException('Could not generate game.')
        else:
            seed = await alttpr(hash_id=hashid)
            if not seed:
                raise SahasrahBotException('Could not retrieve game.')

        embed = await seed.embed(
            name=f"Tournament Qualifier - {date}",
            notes='Below is the permalink for this qualifier\'s race.  Please load the rom and ready up as soon as possible.\n\nRemember, Please do not talk in the qualifier race channels except for the necessary race commands.\nAnything that is a spoiler will result in a forfeit and possible removal from the tournament.\nWhat constitutes a spoiler is at the discretion of the tournament admins.\n',
            emojis=self.bot.emojis)
        await ctx.send(embed=embed)

        await self.send_qualifier_dms(ctx, embed=embed, race=race, url=seed.url, code='/'.join(seed.code))
        await send_irc_message(raceid, 'The seed has been distributed.  Please contact a tournament administrator if you did not receive the seed in Discord.')
        await gsheet_qualifier_start(race=race, date=date)
        for multi in build_multistream_links(race):
            await ctx.send(multi)

    async def finish_qual(self, ctx, raceid):
        date = datetime.datetime.now(timezone('US/Pacific')).date()
        race = await get_race(raceid, complete=True)
        if race == {}:
            raise SahasrahBotException('That race does not exist.')
        if not race['game']['abbrev'] == 'alttphacks':
            raise SahasrahBotException('That is not an alttphacks game.')
        if not race['state'] == 4:
            raise SahasrahBotException('The race has not completed.')

        await gsheet_qualifier_finish(race=race, date=date)


async def loadnicks(ctx):
    agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
    agc = await agcm.authorize()
    wb = await agc.open_by_key(c.TournamentQualifierSheet)
    wks = await wb.get_worksheet(0)

    bad_discord_names = []

    converter = commands.MemberConverter()
    for idx, row in enumerate(await wks.get_all_records()):
        if not row['Nick Loaded'] in ['Y', 'ignore']:
            try:
                member = await converter.convert(ctx, row['Discord Name'])
                await srlnick.insert_srl_nick(member.id, row['SRL Name'])
                await wks.update_cell(idx+2, 6, 'Y')
            except discord.ext.commands.errors.BadArgument:
                bad_discord_names.append(row['Discord Name'])
                await wks.update_cell(idx+2, 6, 'Error')

    if len(bad_discord_names) > 0:
        await ctx.send("Bad discord names.  These names were not processed.\n\n`{names}`".format(
            names='\n'.join(bad_discord_names)
        ))


def build_multistream_links(race):
    twitchnames = []
    for entrant in race['entrants']:
        twitch = race['entrants'][entrant]['twitch']
        if not twitch == "":
            twitchnames.append(twitch)

    chunks = [twitchnames[i * 4:(i + 1) * 4]
              for i in range((len(twitchnames) + 4 - 1) // 4)]
    multi = []
    for chunk in chunks:
        multi.append(
            '<https://multistre.am/{streams}/layout12/>\n'.format(streams='/'.join(chunk)))
    return multi


async def gsheet_qualifier_start(race, date):
    agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
    agc = await agcm.authorize()
    wb = await agc.open_by_key(c.TournamentQualifierSheet)

    raceid = race['id']

    try:
        wks = await wb.worksheet(f'Qualifier - {date} - {raceid}')
        await wks.clear()
    except gspread.exceptions.WorksheetNotFound:
        wks = await wb.add_worksheet(title=f'Qualifier - {date} - {raceid}', rows=50, cols=10)

    await wks.append_row(['Place', 'Nickname', 'Twitch Stream', 'Finish Time', 'Score', 'Notes'])

    for entrant in race['entrants']:
        if entrant == "JOPEBUSTER":
            continue
        twitch = race['entrants'][entrant]['twitch']
        await wks.append_row([9999, entrant, twitch, '', '=IF(ROUND((2-(INDIRECT(\"R[0]C[-1]\", false)/AVERAGE($D$2:$D$6)))*100,2)>105,105,IF(ROUND((2-(INDIRECT(\"R[0]C[-1]\", false)/AVERAGE($D$2:$D$6)))*100,2)<0,0,ROUND((2-(INDIRECT(\"R[0]C[-1]\", false)/AVERAGE($D$2:$D$6)))*100,2)))'], value_input_option='USER_ENTERED')


async def gsheet_qualifier_finish(race, date):
    agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
    agc = await agcm.authorize()
    wb = await agc.open_by_key(c.TournamentQualifierSheet)

    raceid = race['id']

    try:
        wks = await wb.worksheet(f'Qualifier - {date} - {raceid}')
    except gspread.exceptions.WorksheetNotFound:
        await gsheet_qualifier_start(race, date)
        wks = await wb.worksheet(f'Qualifier - {date} - {raceid}')

    for idx, row in enumerate(await wks.get_all_records()):
        try:
            entrant = race['entrants'][row['Nickname']]
        except KeyError:
            continue
        await wks.update_cell(idx+2, 4, entrant['time'])
        await wks.update_cell(idx+2, 1, entrant['place'])


async def get_race(raceid, complete=False):
    # if we're developing locally, we want to have some artifical data to use that isn't from SRL
    if c.DEBUG:
        if raceid == "test":
            async with aiofiles.open('test_input/srl_test.json', 'r') as f:
                return json.loads(await f.read(), strict=False)
        elif raceid == "test2" and not complete:
            async with aiofiles.open('test_input/srl_open.json', 'r') as f:
                return json.loads(await f.read(), strict=False)
        elif raceid == "test2" and complete:
            async with aiofiles.open('test_input/srl_complete.json', 'r') as f:
                return json.loads(await f.read(), strict=False)
        elif raceid == 'rip':
            return {}

    return await http.request_generic(f'http://api.speedrunslive.com/races/{raceid}', returntype='json')


async def send_irc_message(raceid, message):
    await srlbot.message(f'#srl-{raceid}', message)

# def srl_race_id(channel):
#     if re.search('^#srl-[a-z0-9]{5}$', channel):
#         return channel.partition('-')[-1]


def get_creds():
    return ServiceAccountCredentials.from_json_keyfile_dict(c.gsheet_api_oauth,
                                                            ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive',
                                                             'https://www.googleapis.com/auth/spreadsheets'])


def setup(bot):
    bot.add_cog(TournamentQualifier(bot))
