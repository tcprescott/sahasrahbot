"""Building the MCP server.

Built from ``mount()`` rather than at import: ``MCPServer.__init__`` configures
logging, which at import time would beat the app's own setup.
"""

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import Tool as MCPTool

from alttprbot_api.mcp.auth import optional_actor
from alttprbot_api.mcp.registry import write_tool_names
from alttprbot_api.mcp.tools import register_all

INSTRUCTIONS = """\
Access to SahasrahBot, the Discord and racetime.gg bot of the A Link to the Past \
Randomizer community. You can list and read seed presets, roll seeds from them \
(ALTTPR, ALTTPR mystery, Super Metroid and SMZ3), look up a seed by its hash, \
vote in and run Discord elections, submit and moderate triforce texts, submit \
tournament race settings, and manage the voice roles of servers you administer.

Everything acts as the Discord user who connected you. Start with `whoami`: it \
says who that is and whether this connection may make changes. A read-only \
connection only sees the tools that read (rolling a seed counts as reading). \
Confirm with the user before a change other people will see, such as publishing \
or closing an election, and never guess an id: read it first.

Discord ids are strings, because they don't fit in a JSON number. Times are UTC.\
"""


class SahasrahBotMCP(MCPServer):
    """Hides the tools that change data from a read-only connection. They're refused
    anyway (``registry.py``); hiding them stops the model planning work it can't do."""

    async def list_tools(self) -> list[MCPTool]:
        tools = await super().list_tools()
        actor = optional_actor()
        if actor is None or not actor.read_only:
            return tools
        hidden = write_tool_names()
        return [tool for tool in tools if tool.name not in hidden]


def build_server() -> MCPServer:
    mcp = SahasrahBotMCP(name='SahasrahBot', instructions=INSTRUCTIONS)
    register_all(mcp)
    return mcp


def new_session_manager(mcp: MCPServer):
    """A fresh transport session manager for one run of the app. Each can run only once."""
    # Called for its side effect: it creates the session manager that asgi.py drives.
    mcp.streamable_http_app(
        # Required, not a tuning knob: a stateful session would run later requests as the first one's caller.
        stateless_http=True,
        json_response=True,
        streamable_http_path='/',
        # The reverse proxy terminates TLS and Host; the default check would refuse every production request.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    return mcp.session_manager
