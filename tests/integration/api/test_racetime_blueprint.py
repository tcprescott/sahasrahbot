"""Route tests for the racetime command-injection endpoint.

See alttprbot/presentation/api/blueprints/racetime.py (/api/racetime/cmd).
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

from alttprbot.presentation.api.blueprints import racetime as rt_bp
from alttprbot.presentation.racetime.compat import HandlerTask


def grant_auth(monkeypatch, access=SimpleNamespace(id=1)):
    mock = AsyncMock(return_value=access)
    monkeypatch.setattr(rt_bp.models.AuthorizationKeyPermissions, "get_or_none", mock)
    return mock


async def test_invalid_auth_key_returns_403(client, monkeypatch):
    auth_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(rt_bp.models.AuthorizationKeyPermissions, "get_or_none", auth_mock)
    resp = await client.post(
        "/api/racetime/cmd?auth_key=bad",
        json={"category": "alttpr", "room": "r1", "cmd": "!help"},
    )
    assert resp.status_code == 403
    # Authorization is scoped per category/type: pin the exact lookup so a
    # broadening regression (dropping subtype, swapping type) would fail.
    auth_mock.assert_awaited_once_with(auth_key__key="bad", type="racetimecmd", subtype="alttpr")


async def test_unhandled_room_returns_404(client, monkeypatch):
    grant_auth(monkeypatch)
    monkeypatch.setattr(rt_bp.racetimebot, "racetime_bots", {"alttpr": SimpleNamespace(handlers={})})
    resp = await client.post(
        "/api/racetime/cmd?auth_key=ok",
        json={"category": "alttpr", "room": "ghost", "cmd": "!help"},
    )
    assert resp.status_code == 404


async def test_success_dispatches_fake_chat_message(client, monkeypatch):
    grant_auth(monkeypatch)
    handler = SimpleNamespace(send_message=AsyncMock(), chat_message=AsyncMock())
    bot = SimpleNamespace(handlers={"alttpr/room1": HandlerTask(task=None, handler=handler)})
    monkeypatch.setattr(rt_bp.racetimebot, "racetime_bots", {"alttpr": bot})

    resp = await client.post(
        "/api/racetime/cmd?auth_key=ok",
        json={"category": "alttpr", "room": "room1", "cmd": "!roll open"},
    )

    assert resp.status_code == 200
    assert (await resp.get_json())["success"] is True
    # The bot announces the command before dispatching the synthetic chat event.
    handler.send_message.assert_awaited_once_with("Executing command from API request: !roll open")
    handler.chat_message.assert_awaited_once()
    fake_data = handler.chat_message.await_args.args[0]
    assert fake_data["type"] == "message.chat"
    assert fake_data["message"]["message"] == "!roll open"
    assert fake_data["message"]["is_monitor"] is True


async def test_unknown_category_raises(client, monkeypatch):
    grant_auth(monkeypatch)
    # category not present in the registry -> source raises Exception -> 500.
    monkeypatch.setattr(rt_bp.racetimebot, "racetime_bots", {})
    resp = await client.post(
        "/api/racetime/cmd?auth_key=ok",
        json={"category": "alttpr", "room": "room1", "cmd": "!help"},
    )
    assert resp.status_code == 500
