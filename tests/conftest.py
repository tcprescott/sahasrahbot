"""Shared pytest setup.

SahasrahBot reads settings from a gitignored ``config.py`` at import time. When
that file is absent (CI, a fresh clone, a cloud agent session), load
``config.example.py`` in its place so modules can be imported with harmless
placeholder values. A real local ``config.py`` is used as-is.

``alttprbot/util/gsheet.py`` builds a Google Drive client at import time from a
service-account key. The placeholder key is empty, so that client is stubbed out
for the test run; no test talks to Google.
"""

import importlib.util
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_example_config() -> None:
    if (ROOT / "config.py").exists() or "config" in sys.modules:
        return
    spec = importlib.util.spec_from_file_location("config", ROOT / "config.example.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules["config"] = module


def _stub_google_clients() -> None:
    try:
        import googleapiclient.discovery
        import oauth2client.service_account
    except ImportError:
        return
    mock.patch.object(
        oauth2client.service_account.ServiceAccountCredentials,
        "from_json_keyfile_dict",
        return_value=None,
    ).start()
    mock.patch.object(googleapiclient.discovery, "build", return_value=mock.MagicMock()).start()


_install_example_config()
_stub_google_clients()


# ---------------------------------------------------------------------------
# Fixtures shared by the unit tests.
#
# Everything above runs at import time so that modules can be imported at all.
# The fixtures below are for the in-process unit tests; see "Checking your work"
# in CLAUDE.md.
# ---------------------------------------------------------------------------


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _repo_cwd(monkeypatch):
    """Run every test from the repo root: preset paths like ``presets/alttpr`` are relative."""
    monkeypatch.chdir(ROOT)


@pytest.fixture(autouse=True)
async def _clear_caches():
    """aiocache memory caches are module globals; don't let one test's entries leak into the next."""
    yield
    for name in (
        "alttprbot.util.asynctournament",
        "alttprbot_discord.util.guild_config",
        "alttprbot.database.role",
        "alttprbot.database.smz3_multiworld",
        "alttprbot.database.tournament_results",
    ):
        module = sys.modules.get(name)
        if module is not None and hasattr(module, "CACHE"):
            await module.CACHE.clear()
    generator = sys.modules.get("alttprbot.alttprgen.generator")
    if generator is not None:
        await generator.get_global_preset_list.cache.clear()


@pytest.fixture
async def db():
    """A fresh in-memory SQLite database with every model's table, for one test.

    Production runs MySQL. SQLite is close enough for ORM-level behaviour, but
    raw MySQL SQL (``ON DUPLICATE KEY``, ``TIMESTAMPADD``) won't run here.
    """
    from tortoise import Tortoise

    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["alttprbot.models"]},
        use_tz=True,
        timezone="UTC",
    )
    await Tortoise.generate_schemas()
    try:
        yield
    finally:
        await Tortoise.close_connections()


@pytest.fixture
def raw_sql(db, monkeypatch):
    """Route ``alttprbot.util.orm`` (MySQL ``%s`` placeholders) to the SQLite test database."""
    from tortoise import Tortoise

    from alttprbot.util import orm

    async def select(sql, args=None):
        conn = Tortoise.get_connection("default")
        return await conn.execute_query_dict(sql.replace("%s", "?"), args)

    async def execute(sql, args=None):
        conn = Tortoise.get_connection("default")
        await conn.execute_query(sql.replace("%s", "?"), args)

    monkeypatch.setattr(orm, "select", select)
    monkeypatch.setattr(orm, "execute", execute)
    return orm


class FakeHTTPServer:
    """A real local HTTP server for code that builds its own aiohttp sessions.

    Queue responses with ``add(method, path, ...)``; the last response queued for
    a route is repeated. Every request is recorded in ``requests`` as a
    SimpleNamespace(method, path, query, body). Point the code at ``url(path)``,
    usually by monkeypatching the config value it builds URLs from.
    """

    def __init__(self):
        self.routes = {}
        self.requests = []
        self.base_url = None

    def add(self, method, path, body="", status=200, content_type="application/json"):
        self.routes.setdefault((method.upper(), path), []).append((status, body, content_type))

    def url(self, path=""):
        return f"{self.base_url}{path}"

    async def _handle(self, request):
        from types import SimpleNamespace

        from aiohttp import web

        body = await request.text()
        self.requests.append(SimpleNamespace(method=request.method, path=request.path, query=dict(request.query), body=body))
        queue = self.routes.get((request.method, request.path))
        if not queue:
            return web.Response(status=404, text="no fake route")
        status, text, content_type = queue[0] if len(queue) == 1 else queue.pop(0)
        return web.Response(status=status, text=text, content_type=content_type)


@pytest.fixture
async def fake_http():
    from aiohttp import web

    server = FakeHTTPServer()
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", server._handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    server.base_url = f"http://127.0.0.1:{port}"
    try:
        yield server
    finally:
        await runner.cleanup()
