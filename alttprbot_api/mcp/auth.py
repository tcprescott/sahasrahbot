"""Who an MCP tool call acts as.

``asgi.py`` checks the bearer token and binds the caller here before handing the
request to the transport; the tool reads it back. That works because the server is
stateless: each request runs its own server task, which copies this context. A
stateful session would serve later requests under the first one's caller.
"""

from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class McpActor:
    discord_user_id: int
    user_name: str
    read_only: bool
    client_name: str

    @property
    def author(self) -> str:
        """How the web app names someone who submits something (``name#discriminator``)."""
        return f"{self.user_name}#0"


_actor: ContextVar[Optional[McpActor]] = ContextVar('mcp_actor', default=None)


def set_actor(actor: McpActor) -> Token:
    return _actor.set(actor)


def reset_actor(token: Token) -> None:
    _actor.reset(token)


def optional_actor() -> Optional[McpActor]:
    return _actor.get()


def current_actor() -> McpActor:
    actor = _actor.get()
    if actor is None:
        raise PermissionError('Not signed in.')
    return actor
