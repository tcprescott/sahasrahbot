import urllib.parse

import config

TORTOISE_ORM = {
    "connections": {
        "default": f'mysql://{config.DB_USER}:{urllib.parse.quote(config.DB_PASS, safe="")}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}'},
    "use_tz": True,
    "timezone": "UTC",
    "apps": {
        "models": {
            "models": ["alttprbot.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
