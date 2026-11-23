"""The standalone dev server (devserver/) builds, and its fakes behave.

Runs in a fresh interpreter because ``devserver.bootstrap.create_app`` installs
its own ``config`` and swaps the Discord bot for a fake. No database is needed:
these routes don't query it.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_SCRIPT = r"""
import asyncio, sys
sys.path.insert(0, {root!r})
from devserver.bootstrap import create_app
from devserver import fixtures

app = create_app("http://localhost:5001")

import alttprbot_discord.bot as bot_module
from alttprbot_api.util import checks
from alttprbot.util import discord_members
from devserver.fake_discord import FakeDiscordBot
assert isinstance(bot_module.discordbot, FakeDiscordBot)
assert checks.discordbot is bot_module.discordbot, "blueprints must see the fake bot"

async def main():
    client = app.test_client()
    admin = fixtures.user("admin")

    # Discord OAuth: code -> token -> /users/@me
    r = await client.post("/_fake/discord/api/oauth2/token", form={{"grant_type": "authorization_code", "code": f"dev-{{admin['id']}}"}})
    assert r.status_code == 200, r.status_code
    token = (await r.get_json())["access_token"]
    r = await client.get("/_fake/discord/api/users/@me", headers={{"Authorization": f"Bearer {{token}}"}})
    me = await r.get_json()
    assert me["id"] == str(admin["id"]) and me["username"] == admin["name"], me
    r = await client.get("/_fake/discord/api/users/@me", headers={{"Authorization": "Bearer nope"}})
    assert r.status_code == 401

    # The authorize page redirects back with a code when a user is chosen.
    r = await client.get(f"/_fake/discord/api/oauth2/authorize?redirect_uri=http://x/cb&state=s&user_id={{admin['id']}}")
    assert r.status_code == 302 and f"code=dev-{{admin['id']}}" in r.headers["Location"], r.headers.get("Location")

    # racetime OAuth
    rt = fixtures.RACETIME_USERS[0]
    r = await client.post("/_fake/racetime/o/token", form={{"code": f"rt-{{rt['id']}}"}})
    token = (await r.get_json())["access_token"]
    r = await client.get("/_fake/racetime/o/userinfo", headers={{"Authorization": f"Bearer {{token}}"}})
    assert (await r.get_json())["id"] == rt["id"]

    # SpeedGaming schedule answers with text/html, like the real API.
    r = await client.get("/_fake/speedgaming/api/schedule?event=x&from=2024-01-01T00:00:00Z&to=2024-01-01T06:00:00Z")
    assert r.mimetype == "text/html"
    assert len(__import__("json").loads(await r.get_data(as_text=True))) == 4

    # Member lookups go through discord_members, as in production.
    guild = bot_module.discordbot.get_guild(fixtures.GUILD_ID)
    member = await discord_members.get_member(guild, fixtures.user("mod")["id"])
    assert fixtures.ROLE_ASYNC_MOD in [r.id for r in member.roles]
    assert await discord_members.get_member(guild, fixtures.user("outsider")["id"]) is None

    # Roles can be changed at runtime.
    r = await client.post(f"/_dev/members/{{fixtures.user('outsider')['id']}}",
                          json={{"guild_id": fixtures.GUILD_ID, "roles": ["Voter"]}})
    assert (await r.get_json())["memberships"][str(fixtures.GUILD_ID)] == ["Voter"]

    # Sending to a channel lands in the outbox.
    await bot_module.discordbot.get_channel(fixtures.CHANNEL_GENERAL).send("hello")
    r = await client.get("/_dev/api/outbox")
    assert (await r.get_json())[-1]["content"] == "hello"

asyncio.run(main())
print("ok")
"""


def test_devserver_fakes():
    code = _SCRIPT.format(root=str(ROOT))
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0 and "ok" in result.stdout, result.stderr[-4000:]
