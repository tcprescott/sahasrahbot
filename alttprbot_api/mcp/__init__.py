"""The MCP server at ``/mcp``, so AI clients like Claude can use SahasrahBot as the
person who connected them. Another entry surface beside the web app and the REST
API: its tools call the same services, and it holds no rules of its own.

It shares the Quart app's port. ``mount()`` wraps the app's ASGI callable so that
``/mcp``, the OAuth routes and the ``/.well-known`` documents go to the MCP SDK and
everything else to Quart, and runs the SDK's session manager for the app's life.
"""

import asyncio
import logging

from quart import Quart
from starlette.routing import Match

import config
from alttprbot_api.mcp import oauth, wellknown
from alttprbot_api.mcp.asgi import McpEndpoint
from alttprbot_api.mcp.server import build_server, new_session_manager

logger = logging.getLogger(__name__)

MCP_PATHS = (wellknown.MCP_PATH, wellknown.MCP_PATH + '/')


class McpDispatcher:
    """Sends MCP traffic to the SDK and the rest to Quart's own ASGI app."""

    def __init__(self, app, endpoint, routes) -> None:
        self.app = app
        self.endpoint = endpoint
        self.routes = routes

    async def __call__(self, scope, receive, send) -> None:
        if scope['type'] == 'http':
            if scope['path'] in MCP_PATHS:
                await self.endpoint(scope, receive, send)
                return
            for route in self.routes:
                match, child = route.matches(scope)
                if match is Match.FULL:
                    await route.handle({**scope, **child}, receive, send)
                    return
        await self.app(scope, receive, send)


def mount(app: Quart) -> None:
    if not config.MCP_ENABLED:
        logger.info('MCP server off (MCP_ENABLED is False)')
        return
    server = build_server()
    endpoint = McpEndpoint()
    app.asgi_app = McpDispatcher(app.asgi_app, endpoint, wellknown.routes() + oauth.routes())

    running: dict = {}

    async def run_sessions(manager, started: asyncio.Event, stop: asyncio.Event) -> None:
        # Its own task, because the transport's task group must be entered and left in one task.
        async with manager.run():
            endpoint.session_manager = manager
            started.set()
            await stop.wait()
            endpoint.session_manager = None

    @app.before_serving
    async def start_mcp_sessions():
        started, stop = asyncio.Event(), asyncio.Event()
        task = asyncio.create_task(run_sessions(new_session_manager(server), started, stop), name='mcp-sessions')
        running.update(task=task, stop=stop)
        await asyncio.wait({task, asyncio.create_task(started.wait())}, return_when=asyncio.FIRST_COMPLETED)
        if task.done():
            task.result()

    @app.after_serving
    async def stop_mcp_sessions():
        if 'task' in running:
            running.pop('stop').set()
            await running.pop('task')

    logger.info('MCP server mounted at %s', wellknown.MCP_PATH)
