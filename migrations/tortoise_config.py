import os
import urllib.parse

from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_NAME = os.environ.get("DB_NAME", "sahasrahbot")
DB_USER = os.environ.get("DB_USER", "user")
DB_PASS = urllib.parse.quote_plus(os.environ.get("DB_PASS", "pass"))

TORTOISE_ORM = {
    "connections": {"default": f'mysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'},
    "apps": {
        "models": {
            "models": ["alttprbot.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
