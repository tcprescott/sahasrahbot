from ..util.alttpr_discord import alttpr
from config import Config as c
from ..util import speedgaming

from time import perf_counter 

import gspread.exceptions
import gspread_asyncio
from oauth2client.service_account import ServiceAccountCredentials

async def get_settings(episodeid, guildid):
    agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
    agc = await agcm.authorize()
    wb = await agc.open_by_key(c.Tournament[guildid]['schedule_sheet'])
    wks = await wb.get_worksheet(0)
 
    for row in await wks.get_all_records():
        if row['SpeedGaming Episode ID'] == int(episodeid):
            return row
    return None

async def generate_game(episodeid, guildid):
    episode = await speedgaming.get_episode(episodeid)

    if 'error' in episode:
        raise Exception(episode["error"])

    if not episode['event']['slug'] == 'alttpr':
        raise Exception('Not an alttpr tournament race.')

    sheet_settings = await get_settings(episodeid, guildid)

    if sheet_settings is None:
        raise Exception('Settings submission not found at <https://docs.google.com/spreadsheets/d/1GHBnuxdLgBcx4llvHepQjwd8Q1ASbQ_4J8ubblyG-0c/edit#gid=941774009>.  Please submit settings at <http://bit.ly/2Dbr9Kr>')

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

    seed = await alttpr(settings=settings)

    return seed, sheet_settings['Game Number'], episode['match1']['players']

def get_creds():
   return ServiceAccountCredentials.from_json_keyfile_dict(c.gsheet_api_oauth,
      ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive',
      'https://www.googleapis.com/auth/spreadsheets'])