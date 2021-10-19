import os
import json


class Config:
    DEBUG = os.environ.get("DEBUG", "False") == "True"

    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", "3306"))
    DB_NAME = os.environ.get("DB_NAME", "sahasrahbot")
    DB_USER = os.environ.get("DB_USER", "user")
    DB_PASS = os.environ.get("DB_PASS", "pass")

    DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")

    baseurl = os.environ.get("ALTTPR_BASEURL")
    seed_baseurl = os.environ.get("ALTTPR_SEED_BASEURL")
    username = os.environ.get("ALTTPR_USERNAME", None)
    password = os.environ.get("ALTTPR_PASSWORD", None)

    SpoilerLogLocal = os.environ.get("SpoilerLogLocal")
    SpoilerLogUrlBase = os.environ.get('SpoilerLogUrlBase')

    SgApiEndpoint = os.environ.get("SgApiEndpoint")

    MultiworldRomBase = os.environ.get("MultiworldRomBase")
    MultiworldHostBase = os.environ.get("MultiworldHostBase")

    gsheet_api_oauth = json.loads(os.environ.get("gsheet_api_oauth"))

    SB_TWITCH_TOKEN = os.environ.get("SB_TWITCH_TOKEN")
    SB_TWITCH_CLIENT_ID = os.environ.get("SB_TWITCH_CLIENT_ID")
    SB_TWITCH_NICK = os.environ.get("SB_TWITCH_NICK")
    SB_TWITCH_PREFIX = os.environ.get("SB_TWITCH_PREFIX")
    SB_TWITCH_CHANNELS = os.environ.get("SB_TWITCH_CHANNELS").split(',')

    RACETIME_CLIENT_ID = os.environ.get("RACETIME_CLIENT_ID")
    RACETIME_CLIENT_SECRET = os.environ.get("RACETIME_CLIENT_SECRET")
    RACETIME_COMMAND_PREFIX = os.environ.get("RACETIME_COMMAND_PREFIX")

    RACETIME_CLIENT_ID_SMZ3 = os.environ.get("RACETIME_CLIENT_ID_SMZ3")
    RACETIME_CLIENT_SECRET_SMZ3 = os.environ.get("RACETIME_CLIENT_SECRET_SMZ3")
