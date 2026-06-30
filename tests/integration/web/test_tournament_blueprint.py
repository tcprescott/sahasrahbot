"""Route tests for the web (session-based) tournament submission endpoint.

See alttprbot/presentation/web/blueprints/tournament.py.
"""


async def test_submit_without_session_is_unauthenticated(client):
    resp = await client.post("/api/tournament/submit", json={"event": "x", "episodeid": 1})
    assert resp.status_code == 401
    assert (await resp.get_json())["error"] == "unauthenticated"
