"""The one way tools get onto the MCP server.

``register`` declares whether a tool changes data (``write=True``). That one flag
sets the ``readOnlyHint`` clients read, refuses the call on a read-only connection,
and hides the tool from one (``server.py``). It also wraps the call in Sentry tags
and the ``mcp.tools`` metrics, and turns service errors into tool errors.
``tests/test_mcp.py`` checks every listed tool went through here.
"""

import functools
from dataclasses import dataclass
from typing import Callable

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from alttprbot.observability import metrics
from alttprbot.services import audit
from alttprbot.observability.sentry import sentry_tags
from alttprbot_api.mcp.auth import current_actor
from alttprbot_api.mcp.errors import map_service_error

READ_ONLY_REFUSAL = ('read_only: This connection was approved for reading only. To let it make changes, '
                     'disconnect it on the SahasrahBot API access page, connect again, and tick '
                     '"Also let it make changes as you".')


@dataclass(frozen=True)
class ToolSpec:
    write: bool
    destructive: bool


TOOL_SPECS: dict[str, ToolSpec] = {}


def write_tool_names() -> frozenset[str]:
    return frozenset(name for name, spec in TOOL_SPECS.items() if spec.write)


def register(mcp: MCPServer, fn: Callable, *, title: str, write: bool = False, destructive: bool = False,
             open_world: bool = False) -> None:
    name = fn.__name__

    @functools.wraps(fn)
    async def tool(*args, **kwargs):
        actor = current_actor()
        if write and actor.read_only:
            raise ToolError(READ_ONLY_REFUSAL)
        source = audit.Source(via=audit.VIA_MCP, detail=actor.client_name, actor_discord_id=actor.discord_user_id,
                              actor_name=actor.user_name)
        with sentry_tags(mcp_tool=name, discord_user_id=actor.discord_user_id), \
                metrics.timed('mcp.tools', {'tool': name}), audit.acting(source):
            try:
                return await fn(*args, **kwargs)
            except Exception as exc:
                raise map_service_error(exc, name) from exc

    mcp.add_tool(tool, name=name, title=title, annotations=ToolAnnotations(
        title=title, readOnlyHint=not write, destructiveHint=destructive, idempotentHint=not (write or open_world),
        openWorldHint=open_world))
    TOOL_SPECS[name] = ToolSpec(write=write, destructive=destructive)
