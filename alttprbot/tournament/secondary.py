import gspread.exceptions
import gspread_asyncio
from oauth2client.service_account import ServiceAccountCredentials
import discord
from discord.ext import commands
from ..database import srlnick
from config import Config as c

async def loadnicks(ctx):
    agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
    agc = await agcm.authorize()
    wb = await agc.open_by_key(c.Tournament[ctx.guild.id]['registration_sheet'])
    wks = await wb.get_worksheet(0)

    bad_discord_names=[]

    for idx, row in enumerate(await wks.get_all_records()):
        if not row['Nick Loaded'] in ['Y','ignore']:
            try:
                member = await commands.MemberConverter().convert(ctx, row['Discord Name'])
                player_role = await commands.RoleConverter().convert(ctx, c.Tournament[ctx.guild.id]['player_role'])
                await srlnick.insert_srl_nick(member.id, row['SRL Name'])
                await srlnick.insert_twitch_name(member.id, row['Twitch Name'])
                await member.add_roles(player_role)
                await wks.update_cell(idx+2, 5, 'Y')
            except discord.ext.commands.errors.BadArgument as e:
                bad_discord_names.append(row['Discord Name'])
                await wks.update_cell(idx+2, 5, 'Error')

    if len(bad_discord_names) > 0:
        await ctx.send("Bad discord names.  These names were not processed.\n\n`{names}`".format(
            names='\n'.join(bad_discord_names)
        ))

def get_creds():
   return ServiceAccountCredentials.from_json_keyfile_dict(c.gsheet_api_oauth,
      ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive',
      'https://www.googleapis.com/auth/spreadsheets'])