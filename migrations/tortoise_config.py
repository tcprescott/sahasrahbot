import os
import urllib.parse

import config

TORTOISE_ORM = {
    "connections": {"default": f'mysql://{config.DB_USER}:{urllib.parse.quote_plus(config.DB_PASS)}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}'},
    "apps": {
        "models": {
            "models": ["alttprbot.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
