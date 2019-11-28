import gspread.exceptions
import gspread_asyncio
from oauth2client.service_account import ServiceAccountCredentials
import discord
from discord.ext import commands
from ..database import srlnick
from config import Config as c
import pyz3r

async def get_settings(episodeid, guildid):
    agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
    agc = await agcm.authorize()
    wb = await agc.open_by_key(c.Tournament[guildid]['schedule_sheet'])
    wks = await wb.worksheet('Schedule')
 
    for row in await wks.get_all_records():
        if row['Game ID'] == episodeid:
            return row
    return None

async def generate_game(episodeid, guildid):
    sheet_settings = await get_settings(episodeid, guildid)

    if sheet_settings is None:
        raise Exception('Episode not found.  Submit settings first.')

    settingsmap = {
        'Standard': 'standard',
        'Maps/Compasses': 'mc',
        'Defeat Ganon': 'ganon',
        'Fast Ganon': 'fast_ganon',
        '7/7': '7',
        '6/6': '6',
        'Open': 'open',
        'Randomized': 'randomized',
        'Assured': 'assured'
    }

    settings = {
            "glitches": "none",
            "item_placement": "advanced",
            "dungeon_items": settingsmap[sheet_settings['Dungeon Item Shuffle']],
            "accessibility": "items",
            "goal": settingsmap[sheet_settings['Goal']],
            "crystals": {
                "ganon": settingsmap[sheet_settings['GT/Ganon Crystals']],
                "tower": settingsmap[sheet_settings['GT/Ganon Crystals']],
            },
            "mode": settingsmap[sheet_settings['World State']],
            "entrances": "none",
            "hints": "off",
            "weapons": settingsmap[sheet_settings['Swords']],
            "item": {
                "pool": "normal",
                "functionality": "normal"
            },
            "tournament": True,
            "spoilers": "off",
            "lang":"en",
            "enemizer": {
                "boss_shuffle":"none",
                "enemy_shuffle":"none",
                "enemy_damage":"default",
                "enemy_health":"default"
            }
        }

    seed = await pyz3r.alttpr(
        baseurl=c.baseurl,
        seed_baseurl=c.seed_baseurl,
        username=c.username,
        password=c.password,
        settings=settings
    )

    player1 = await srlnick.get_discord_id_by_twitch(sheet_settings['Player 1'])

    if player1 is False:
        raise Exception(f"Unable to identify {sheet_settings['Player 1']}")

    player2 = await srlnick.get_discord_id_by_twitch(sheet_settings['Player 2'])

    if player2 is False:
        raise Exception(f"Unable to identify {sheet_settings['Player 2']}")

    players = [
        {
            "displayName": sheet_settings['Player 1'],
            "discordId": player1[0]['discord_user_id']
        },
        {
            "displayName": sheet_settings['Player 2'],
            "discordId": player2[0]['discord_user_id']
        }
    ]

    return seed, sheet_settings['Game'], players

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