"""Route tests for the tournament blueprint.

See alttprbot/presentation/api/blueprints/tournament.py.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from alttprbot.presentation.api.blueprints import tournament as t_bp


def fake_event(submission_form):
    cfg = SimpleNamespace(submission_form=submission_form)
    return SimpleNamespace(get_config=AsyncMock(return_value=cfg))


async def test_submit_without_session_is_unauthenticated(client):
    resp = await client.post("/api/tournament/submit", json={"event": "x", "episodeid": 1})
    assert resp.status_code == 401
    assert (await resp.get_json())["error"] == "unauthenticated"


async def test_form_config_unknown_event_returns_404(client):
    resp = await client.get("/api/tournament/form-config/definitely-not-an-event")
    assert resp.status_code == 404


async def test_form_config_no_submission_form_returns_422(client, monkeypatch):
    monkeypatch.setattr(t_bp, "TOURNAMENT_DATA", {"fakeevent": fake_event(None)})
    resp = await client.get("/api/tournament/form-config/fakeevent")
    assert resp.status_code == 422


async def test_form_config_custom_template_returns_422(client, monkeypatch):
    # A string submission_form is a server-rendered template name, unsupported by the JSON API.
    monkeypatch.setattr(t_bp, "TOURNAMENT_DATA", {"fakeevent": fake_event("custom_form.html")})
    resp = await client.get("/api/tournament/form-config/fakeevent")
    assert resp.status_code == 422


async def test_form_config_returns_settings(client, monkeypatch):
    form = [{"name": "vod", "type": "text"}]
    monkeypatch.setattr(t_bp, "TOURNAMENT_DATA", {"fakeevent": fake_event(form)})
    resp = await client.get("/api/tournament/form-config/fakeevent")
    assert resp.status_code == 200
    assert (await resp.get_json())["settings"] == form


async def test_games_forwards_allowlisted_params_to_service(client, monkeypatch):
    captured = {}

    async def fake_search(self, raw_filters):
        captured.update(raw_filters)
        return [{"episode_id": 42, "event": "alttprleague"}]

    monkeypatch.setattr(t_bp.TournamentGamesService, "search", fake_search)

    resp = await client.get("/api/tournament/games?event=alttprleague&episode_id=42")

    assert resp.status_code == 200
    assert await resp.get_json() == [{"episode_id": 42, "event": "alttprleague"}]
    # Query params reach the service, which applies the field allowlist.
    assert captured == {"event": "alttprleague", "episode_id": "42"}
