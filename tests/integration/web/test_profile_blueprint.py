"""Route tests for the profile endpoints: GET /api/me, display-name update,
and RaceTime unlink.

See alttprbot/presentation/web/web.py (api_me) and
alttprbot/presentation/web/blueprints/profile.py.
"""

from unittest.mock import AsyncMock

from alttprbot.presentation.web import web as web_module
from alttprbot.presentation.web.oauth_client import DiscordUser
from alttprbot.services import UserService

DISCORD_USER = DiscordUser({
    "id": "123",
    "username": "tester",
    "global_name": "Tester",
    "discriminator": "0",
    "avatar": None,
})


async def sign_in(client):
    async with client.session_transaction() as session:
        session["discord_oauth_token"] = {"access_token": "tok", "token_type": "Bearer"}


async def test_api_me_unauthenticated_returns_401(client):
    resp = await client.get("/api/me")
    assert resp.status_code == 401
    assert (await resp.get_json())["error"] == "unauthenticated"


async def test_api_me_includes_linked_account_state(client, monkeypatch):
    await sign_in(client)
    monkeypatch.setattr(web_module.discord, "fetch_user", AsyncMock(return_value=DISCORD_USER))
    profile = AsyncMock(return_value=None)
    monkeypatch.setattr(UserService, "get_by_discord_id", profile)

    resp = await client.get("/api/me")
    assert resp.status_code == 200
    data = (await resp.get_json())["data"]
    assert data["display_name"] is None
    assert data["linked_accounts"]["discord"] == {"linked": True, "username": "tester"}
    assert data["linked_accounts"]["racetime"] == {"linked": False, "id": None, "url": None}
    assert data["linked_accounts"]["twitch"] == {"linked": False, "name": None}


async def test_display_name_update_requires_auth(client):
    # @requires_authorization redirects to /login/ rather than 401ing, same as
    # the other session-authenticated web routes (racetime.py, presets.py).
    resp = await client.post("/api/me/display-name", json={"display_name": "Alice"})
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/login/"


async def test_display_name_update_rejects_invalid_name(client, monkeypatch):
    await sign_in(client)
    monkeypatch.setattr(web_module.discord, "fetch_user", AsyncMock(return_value=DISCORD_USER))
    monkeypatch.setattr(UserService, "get_or_create_by_discord_id", AsyncMock(return_value=AsyncMock()))

    resp = await client.post("/api/me/display-name", json={"display_name": "   "})
    assert resp.status_code == 400
    assert "error" in (await resp.get_json())


async def test_display_name_update_succeeds(client, monkeypatch):
    await sign_in(client)
    monkeypatch.setattr(web_module.discord, "fetch_user", AsyncMock(return_value=DISCORD_USER))

    record = AsyncMock()
    record.display_name = "Alice"
    monkeypatch.setattr(UserService, "get_or_create_by_discord_id", AsyncMock(return_value=record))
    update_mock = AsyncMock()
    monkeypatch.setattr(UserService, "update_display_name", update_mock)

    resp = await client.post("/api/me/display-name", json={"display_name": "Alice"})
    assert resp.status_code == 200
    body = await resp.get_json()
    assert body["success"] is True
    update_mock.assert_awaited_once_with(record, "Alice")


async def test_racetime_unlink_requires_auth(client):
    resp = await client.post("/api/me/racetime/unlink")
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/login/"


async def test_racetime_unlink_succeeds(client, monkeypatch):
    await sign_in(client)
    monkeypatch.setattr(web_module.discord, "fetch_user", AsyncMock(return_value=DISCORD_USER))
    unlink_mock = AsyncMock()
    monkeypatch.setattr(UserService, "unlink_racetime_account", unlink_mock)

    resp = await client.post("/api/me/racetime/unlink")
    assert resp.status_code == 200
    assert (await resp.get_json())["success"] is True
    unlink_mock.assert_awaited_once_with(123)


async def test_racetime_unlink_returns_400_when_not_linked(client, monkeypatch):
    await sign_in(client)
    monkeypatch.setattr(web_module.discord, "fetch_user", AsyncMock(return_value=DISCORD_USER))
    monkeypatch.setattr(
        UserService, "unlink_racetime_account", AsyncMock(side_effect=ValueError("No RaceTime.gg account is linked."))
    )

    resp = await client.post("/api/me/racetime/unlink")
    assert resp.status_code == 400
    assert "error" in (await resp.get_json())
