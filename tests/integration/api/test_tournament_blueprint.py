"""Route tests for the tournament blueprint.

See alttprbot/presentation/api/blueprints/tournament.py.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from alttprbot.presentation.api.blueprints import tournament as t_bp


def patch_form_config(monkeypatch, submission_form):
    """Make ``fakeevent`` a known event whose dispatched config has ``submission_form``."""
    monkeypatch.setattr(t_bp.tournament_registry, "TOURNAMENT_DATA", {"fakeevent": object()})
    cfg = SimpleNamespace(submission_form=submission_form)
    monkeypatch.setattr(t_bp.tournament_dispatch, "get_config", AsyncMock(return_value=cfg))


async def test_submit_without_session_is_unauthenticated(client):
    resp = await client.post("/api/tournament/submit", json={"event": "x", "episodeid": 1})
    assert resp.status_code == 401
    assert (await resp.get_json())["error"] == "unauthenticated"


async def test_form_config_unknown_event_returns_404(client):
    resp = await client.get("/api/tournament/form-config/definitely-not-an-event")
    assert resp.status_code == 404


async def test_form_config_no_submission_form_returns_422(client, monkeypatch):
    patch_form_config(monkeypatch, None)
    resp = await client.get("/api/tournament/form-config/fakeevent")
    assert resp.status_code == 422


async def test_form_config_custom_template_returns_422(client, monkeypatch):
    # A string submission_form is a server-rendered template name, unsupported by the JSON API.
    patch_form_config(monkeypatch, "custom_form.html")
    resp = await client.get("/api/tournament/form-config/fakeevent")
    assert resp.status_code == 422


async def test_form_config_returns_settings(client, monkeypatch):
    form = [{"name": "vod", "type": "text"}]
    patch_form_config(monkeypatch, form)
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
