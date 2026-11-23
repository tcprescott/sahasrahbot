"""Build the SahasrahBot web app wired to fakes instead of real services.

Order matters, because the app reads its settings and binds ``discordbot`` at
import time:

1. Load ``config.example.py`` as ``config`` (never the real ``config.py``) and
   point every external URL at this server's ``/_fake/`` routes.
2. Stub the Google Sheets client and point quart-discord at the fake Discord.
3. Swap ``alttprbot_discord.bot.discordbot`` for ``FakeDiscordBot`` *before*
   anything imports it from there.
4. Import ``alttprbot_api.api`` and add the fake-service and ``/_dev`` blueprints.

Production code is not modified; nothing here runs unless the dev server does.
"""
import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
logger = logging.getLogger("devserver")


def load_config(app_url: str):
    if "config" in sys.modules and not getattr(sys.modules["config"], "_SAHASRAHBOT_DEV", False):
        raise RuntimeError("config was imported before the dev server could install its own")
    spec = importlib.util.spec_from_file_location("config", ROOT / "config.example.py")
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    config._SAHASRAHBOT_DEV = True
    config.DEBUG = True
    config.APP_URL = app_url
    config.APP_SECRET_KEY = "sahasrahbot-dev-server"
    config.DISCORD_CLIENT_ID = "1000"
    config.DISCORD_CLIENT_SECRET = "dev"
    config.DISCORD_TOKEN = "dev"
    config.RACETIME_URL = f"{app_url}/_fake/racetime"
    config.RACETIME_CLIENT_ID_OAUTH = "dev"
    config.RACETIME_CLIENT_SECRET_OAUTH = "dev"
    config.SG_API_ENDPOINT = f"{app_url}/_fake/speedgaming/api"
    sys.modules["config"] = config
    return config


def stub_google():
    import googleapiclient.discovery
    import oauth2client.service_account

    mock.patch.object(oauth2client.service_account.ServiceAccountCredentials, "from_json_keyfile_dict",
                      return_value=None).start()
    mock.patch.object(googleapiclient.discovery, "build", return_value=mock.MagicMock()).start()


def point_quart_discord_at_fake(app_url: str):
    from quart_discord import configs

    base = f"{app_url}/_fake/discord"
    configs.DISCORD_API_BASE_URL = f"{base}/api"
    configs.DISCORD_AUTHORIZATION_BASE_URL = f"{base}/api/oauth2/authorize"
    configs.DISCORD_TOKEN_URL = f"{base}/api/oauth2/token"
    configs.DISCORD_IMAGE_BASE_URL = f"{base}/"
    configs.DISCORD_EMBED_BASE_BASE_URL = f"{base}/"
    configs.DISCORD_USER_AVATAR_BASE_URL = f"{base}/avatars/{{user_id}}/{{avatar_hash}}.{{format}}"
    configs.DISCORD_DEFAULT_USER_AVATAR_BASE_URL = f"{base}/avatars/0/default.png"


def install_fake_bot():
    from devserver import fixtures
    from devserver.fake_discord import FakeDiscordBot

    world = fixtures.build_world()
    fake = FakeDiscordBot(world)

    import alttprbot_discord.bot as bot_module

    real = bot_module.discordbot
    bot_module.discordbot = fake
    return world, fake, real


def _replace_lingering_bot(real, fake):
    """Catch any module that imported the real bot before the swap."""
    for name, module in list(sys.modules.items()):
        if name.startswith(("alttprbot", "devserver")) and getattr(module, "discordbot", None) is real:
            logger.warning("Replacing real discordbot imported early by %s", name)
            module.discordbot = fake


_DEV_BADGE = (
    '<a href="/_dev/" id="sahasrahbot-dev-badge" style="position:fixed;right:12px;bottom:12px;z-index:99999;'
    'background:#e0a800;color:#000;padding:4px 10px;border-radius:12px;font:600 12px sans-serif;'
    'text-decoration:none;box-shadow:0 1px 4px rgba(0,0,0,.3)">DEV</a>'
)


def create_app(app_url: str):
    load_config(app_url)
    stub_google()
    point_quart_discord_at_fake(app_url)
    world, fake, real = install_fake_bot()

    from alttprbot_api.api import sahasrahbotapi
    from alttprbot_discord import gateways
    from devserver.dev_tools import dev_tools
    from devserver.fake_services import fake_services

    _replace_lingering_bot(real, fake)
    # What sahasrahbot.py does at startup: give services their Discord lookups (here, the fake bot's).
    gateways.register()

    sahasrahbotapi.config["DEV_WORLD"] = world
    sahasrahbotapi.register_blueprint(fake_services)
    sahasrahbotapi.register_blueprint(dev_tools)

    @sahasrahbotapi.after_request
    async def _dev_badge(response):
        # A corner link to /_dev on every app page, so the fake-user tools are one click away.
        from quart import request

        if response.mimetype == "text/html" and not request.path.startswith(("/_dev", "/_fake")):
            body = response.get_data(as_text=True)
            if inspect.isawaitable(body):
                body = await body
            if "</body>" in body:
                response.set_data(body.replace("</body>", _DEV_BADGE + "</body>", 1))
        return response

    return sahasrahbotapi
