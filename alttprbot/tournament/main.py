import datetime

import gspread.exceptions
import gspread_asyncio
from oauth2client.service_account import ServiceAccountCredentials
from pytz import timezone

from alttprbot_discord.util.alttpr_discord import alttpr
from config import Config as c

from ..util import speedgaming

tz = timezone('EST')

class SettingsSubmissionNotFoundException(Exception):
    pass

class InvalidSettingsException(Exception):
    pass

class AlreadyGeneratedException(Exception):
    pass

async def settings_sheet(episodeid, guildid):
    sheet = SettingsSheet(episodeid, guildid)
    await sheet._init()
    return sheet

class SettingsSheet():
    def __init__(self, episodeid, guildid: int):
        self.agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
        self.config = c.Tournament[guildid]
        self.episodeid = episodeid

    async def _init(self):
        self.agc = await self.agcm.authorize()
        self.wb = await self.agc.open_by_key(self.config['schedule_sheet'])
        self.wks = await self.wb.get_worksheet(0)

        self.headers = await self.wks.row_values(1)

        for idx, row in enumerate(await self.wks.get_all_records()):
            if row['SpeedGaming Episode ID'] == int(self.episodeid):
                self.rowid = idx+2
                self.row = row
                return row
        raise SettingsSubmissionNotFoundException('Settings submission not found at <https://docs.google.com/spreadsheets/d/1GHBnuxdLgBcx4llvHepQjwd8Q1ASbQ_4J8ubblyG-0c/edit#gid=941774009>.  Please submit settings at <http://bit.ly/2Dbr9Kr>')
    
    async def write_gen_date(self):
        date_gen_column = self.headers.index('Date Generated')+1
        await self.wks.update_cell(row=self.rowid, col=date_gen_column, value=datetime.datetime.now(tz).isoformat())

    def is_generated(self):
        if not self.row['Date Generated'] == '': return True
        else: return False

    def sanity_check(self):
        count = 0
        if not self.row['Dungeon Item Shuffle'] == 'Standard': count+=1
        if not self.row['Goal'] == 'Defeat Ganon': count+=1
        if not self.row['GT/Ganon Crystals'] == '7/7': count+=1
        if not self.row['World State'] == 'Open': count+=1
        if not self.row['Swords'] == 'Randomized': count+=1

        if self.row['Game Number']==1: return True if count==0 else False
        elif self.row['Game Number']==2: return True if count<=1 else False
        elif self.row['Game Number']==3: return True if count<=2 else False
        else: return False

async def generate_game(episodeid, guildid, force=False):
    episode = await speedgaming.get_episode(int(episodeid))

    sheet_settings = await settings_sheet(episodeid, guildid)

    if not force:
        if not sheet_settings.sanity_check():
            raise InvalidSettingsException("The settings chosen are invalid for this game.  Please contact an Admin to correct the settings.")
        if sheet_settings.is_generated():
            raise AlreadyGeneratedException("This game has already been generated.  Please contact a tournament administrator for assistance.")
        
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
            "dungeon_items": settingsmap[sheet_settings.row['Dungeon Item Shuffle']],
            "accessibility": "items",
            "goal": settingsmap[sheet_settings.row['Goal']],
            "crystals": {
                "ganon": settingsmap[sheet_settings.row['GT/Ganon Crystals']],
                "tower": settingsmap[sheet_settings.row['GT/Ganon Crystals']],
            },
            "mode": settingsmap[sheet_settings.row['World State']],
            "entrances": "none",
            "hints": "off",
            "weapons": settingsmap[sheet_settings.row['Swords']],
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

    await sheet_settings.write_gen_date()
    return seed, sheet_settings.row['Game Number'], episode['match1']['players']



def get_creds():
   return ServiceAccountCredentials.from_json_keyfile_dict(c.gsheet_api_oauth,
      ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive',
      'https://www.googleapis.com/auth/spreadsheets'])
