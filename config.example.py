"""Example configuration for SahasrahBot.

The real ``config.py`` is gitignored because it holds production secrets. Copy
this file to ``config.py`` and fill in what you need to run locally:

    cp config.example.py config.py

Every attribute the code reads from ``config`` is listed here, with a harmless
placeholder, so modules can be imported (and tested) without real credentials.
``tests/conftest.py`` loads this file as ``config`` when no ``config.py`` exists.

Never commit real values to this file.
"""

# --- General -----------------------------------------------------------------
DEBUG = True
APP_URL = "http://localhost:5001"
APP_SECRET_KEY = "dev-secret-key"
SENTRY_URL = None  # Sentry DSN; None disables Sentry.

# --- Database (MySQL via Tortoise ORM) ---------------------------------------
DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "sahasrahbot"
DB_USER = "sahasrahbot"
DB_PASS = ""

# --- Discord -----------------------------------------------------------------
DISCORD_TOKEN = ""
DISCORD_CLIENT_ID = "0"
DISCORD_CLIENT_SECRET = ""

# Comma-separated Discord guild/channel ids.
ALTTP_RANDOMIZER_SERVERS = "0"

# --- racetime.gg -------------------------------------------------------------
RACETIME_HOST = "racetime.gg"
RACETIME_PORT = None
RACETIME_SECURE = True
RACETIME_URL = "https://racetime.gg"
RACETIME_COMMAND_PREFIX = "!"
RACETIME_SESSION_TOKEN = ""
RACETIME_CSRF_TOKEN = ""
RACETIME_CLIENT_ID_OAUTH = ""
RACETIME_CLIENT_SECRET_OAUTH = ""
# Each racetime category bot also reads RACETIME_CLIENT_ID_<SLUG> and
# RACETIME_CLIENT_SECRET_<SLUG> (slug upper-cased, dashes removed), e.g.
# RACETIME_CLIENT_ID_ALTTPR. These are placeholders for every category in
# alttprbot_racetime/config.py; alttprbot_racetime/bot.py refuses to start
# unless every category has both, so a real config.py must set them all.
for _slug in ("test", "alttpr", "ct-jets", "ff1r", "smb3r", "smr", "smz3", "twwr",
              "z1r", "z2r"):
    _key = _slug.upper().replace("-", "")
    globals()[f"RACETIME_CLIENT_ID_{_key}"] = "placeholder"
    globals()[f"RACETIME_CLIENT_SECRET_{_key}"] = "placeholder"
del _slug, _key

# --- SpeedGaming -------------------------------------------------------------
SG_API_ENDPOINT = "https://speedgaming.org/api"
SG_DISCORD_WEBHOOK = ""

# --- Randomizers and seed hosting --------------------------------------------
ALTTPR_BASEURL = "https://alttpr.com"
ALTTPR_USERNAME = ""
ALTTPR_PASSWORD = ""
ALTTP_ROM = ""  # Path to a JP 1.0 ROM, needed by the door randomizer.
MULTIWORLDHOSTBASE = ""
SPOILERLOGURLBASE = ""
SAHASRAHBOT_BUCKET = ""
AWS_SPOILER_BUCKET_NAME = ""

# --- Google Sheets -----------------------------------------------------------
GSHEET_API_OAUTH = {}  # Service-account JSON key as a dict.
TOURNAMENT_RESULTS_SHEET = ""
